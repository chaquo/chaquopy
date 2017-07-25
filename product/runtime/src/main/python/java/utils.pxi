# I considered whether to make `cast` aliases clearly distinguishable from plain objects, by
# generalizing `NoneCast` to `Cast`, and giving it a `repr` of `cast('<jni-signature>',
# repr(<underlying-object>))`. However, this would require the `Cast` type to support all the
# same `__special__` methods as Java objects, and to be kept in sync as those methods are
# expanded in the future, and I don't see any benefit to justify that work.
#
# TODO #5181 provide way to check whether two proxy objects are the same Java object, even if
# one of them has been casted.
def cast(cls, obj):
    """Returns a view of the given object as the given class. The class must a class created by
    :any:`jclass` or :any:`jarray`, or a JNI type signature for a class or array. The object
    must be of a `jclass` or `jarray` type which is assignable to the given class, otherwise
    `TypeError` will be raised. `None` (representing Java `null`) is also accepted.

    Situations where this could be useful:

    * By changing the apparent type of an object:
       * A different overload may be chosen when passing the object to a method.
       * A different overload may be chosen when calling a method on the object itself.
    * By selecting a type for `None`, an ambiguous overload can be resolved.
    """
    sig = java.jni_sig(cls)
    if sig.startswith("L"):
        proxy_type = java.jclass(sig)
    elif sig.startswith("["):
        proxy_type = java.jarray(sig[1:])
    else:
        raise TypeError(f"{type(cls).__name__} object does not specify a Java class or array type")

    if obj is None or isinstance(obj, NoneCast):
        return none_casts[sig]
    else:
        if isinstance(obj, JavaObject):
            instance = obj.j_self
        elif isinstance(obj, JavaArray):  # TODO #5260 cover with JavaObject
            instance = obj.j_self
        else:
            raise TypeError(f"{type(obj).__name__} object is not a Java object or array")
        return proxy_type(instance=instance)


class NoneCast(object):
    def __repr__(self):
        return f"cast('{self.sig}', None)"

class none_cast_dict(dict):
    # Use a different subclass for each type, so overload resolution can be cached.
    def __missing__(self, sig):
        obj = type(str("NoneCast_" + sig),
                   (NoneCast,),
                   {"sig": sig})()
        self[sig] = obj
        return obj

none_casts = none_cast_dict()


# TODO #5167 this may fail in non-Java-created threads on Android, because they'll use the
# wrong ClassLoader.
def find_javaclass(name):
    """Returns the java.lang.Class proxy object corresponding to the given fully-qualified name.
    """
    return java.jclass("java.lang.Class")(instance=CQPEnv().FindClass(name))


cdef str_for_c(s):
    if isinstance(s, unicode):
        return s.encode('utf-8')
    else:
        assert isinstance(s, bytes)
        return s


# TODO #5169 use proxy for actual exception class
class JavaException(Exception):
    """Raised when an exception arises from Java code. The message contains the Java exception
    class and stack trace.
    """


cdef expect_exception(JNIEnv *j_env, msg):
    """Raises a Java exception if one is pending, otherwise raises a Python Exception with the
    given message.
    """
    check_exception(j_env)
    raise Exception(msg)


# TODO #5167 is this thread-safe?
processing_exception = False

cdef check_exception(JNIEnv *j_env):
    env = CQPEnv()
    j_exc = env.ExceptionOccurred()
    if not j_exc:
        return
    env.ExceptionClear()

    try:
        global processing_exception
        if processing_exception:
            raise JavaException("Another exception occurred while getting exception details")
        processing_exception = True

        exc = j2p(env.j_env, j_exc)
        PrintWriter = java.jclass("java.io.PrintWriter")
        StringWriter = java.jclass("java.io.StringWriter")
        sw = StringWriter()
        pw = PrintWriter(sw)
        exc.printStackTrace(pw)
        pw.close()
        raise JavaException(sw.toString())

    finally:
        processing_exception = False


cdef jmethodID mid_getName = NULL

# To avoid infinite recursion, this function must not use anything which could call
# lookup_java_object_name itself, including any jclass proxy methods.
cdef lookup_java_object_name(JNIEnv *j_env, jobject j_obj):
    """Returns the fully-qualified class name of the given object, in the same format as
    Class.getName().
    * Array types are returned in JNI format (e.g. "[Ljava/lang/Object;" or "[I".
    * Other types are returned in Java format (e.g. "java.lang.Object"
    """
    j_cls = LocalRef.adopt(j_env, j_env[0].GetObjectClass(j_env, j_obj))

    global mid_getName
    if not mid_getName:
        j_Class = LocalRef.adopt(j_env, j_env[0].GetObjectClass(j_env, j_cls.obj))
        mid_getName = j_env[0].GetMethodID(j_env, j_Class.obj, 'getName', '()Ljava/lang/String;')
        if not mid_getName:
            j_env[0].ExceptionClear(j_env)
            raise Exception("GetMethodID failed")

    j_name = LocalRef.adopt(j_env, j_env[0].CallObjectMethod(j_env, j_cls.obj, mid_getName))
    if not j_name:
        j_env[0].ExceptionClear(j_env)
        raise Exception("getName failed")
    return j2p_string(j_env, j_name.obj)


def is_applicable(sign_args, args, autobox, varargs):
    if len(args) == len(sign_args):
        pass
    elif varargs:
        if len(args) < len(sign_args) - 1:
            return False
    else:
        return False

    cdef JNIEnv *env = get_jnienv()
    for index, sign_arg in enumerate(sign_args):
        if varargs and (index == len(sign_args) - 1):
            assert sign_arg[0] == "["
            remaining_args = args[index:]
            return is_applicable([sign_arg[1:]] * len(remaining_args),
                                 remaining_args, autobox, False)
        else:
            arg = args[index]
        if not is_applicable_arg(env, sign_arg, arg, autobox):
            return False

    return True


# Because of the caching in JavaMultipleMethod, the result of this function must only be
# affected by the actual parameter type, not its value.
cdef is_applicable_arg(JNIEnv *env, r, arg, autobox):
    if assignable_to_array(r, arg):
        return True
    try:
        p2j(env, r, arg, autobox)
        return True
    except TypeError:
        return False


def better_overload(JavaMethod jm1, JavaMethod jm2, actual_types, *, varargs):
    """Returns whether jm1 is an equal or better match than jm2 for the given actual parameter
    types. This is based on JLS 15.12.2.5. "Choosing the Most Specific Method" and JLS 4.10.
    "Subtyping".
    """
    defs1, defs2 = jm1.definition_args, jm2.definition_args

    if varargs:
        if not actual_types:
            # No arguments were given, so the definitions must both be of the form (X...). Give
            # a fake argument so they can be compared.
            actual_types = [type(None)]
        defs1 = extend_varargs(defs1, len(actual_types))
        defs2 = extend_varargs(defs2, len(actual_types))

    return (len(defs1) == len(defs2) and
            all([better_overload_arg(d1, d2, at)
                 for d1, d2, at in six.moves.zip(defs1, defs2, actual_types)]))


def extend_varargs(defs, length):
    varargs_count = length - (len(defs) - 1)
    vararg_type = defs[-1][1:]
    return defs[:-1] + ((vararg_type,) * varargs_count)


# Because of the caching in JavaMultipleMethod, the result of this function must only be
# affected by the actual parameter types, not their values.
#
# We don't have to handle combinations which will be filtered out by is_applicable_arg. For
# example, we'll never be asked to compare a numeric type with a boolean or char, because any
# actual parameter type which is applicable to one will not be applicable to the others.
#
# In this context, boxed and unboxed types are NOT treated as related.
def better_overload_arg(def1, def2, actual_type):
    if def2 == def1:
        return True

    # To avoid data loss, we prefer to treat a Python int or float as the largest of the
    # corresponding Java types.
    elif issubclass(actual_type, six.integer_types) and (def1 in INT_TYPES) and (def2 in INT_TYPES):
        return INT_TYPES.find(def1) >= INT_TYPES.find(def2)
    elif issubclass(actual_type, float) and (def1 in FLOAT_TYPES) and (def2 in FLOAT_TYPES):
        return FLOAT_TYPES.find(def1) >= FLOAT_TYPES.find(def2)

    # Similarly, we prefer to treat a Python string as a Java String rather than a char.
    # array. (Its length cannot be taken into account: see note above about caching.)
    elif issubclass(actual_type, six.string_types) and \
         def2 in ["C", "Ljava/lang/Character;"] and def1 == "Ljava/lang/String;":
        return True

    # Otherwise we prefer the smallest (i.e. most specific) Java type. This includes the case
    # of passing a Python int where float and double overloads exist: the float overload will
    # be called, just like in Java.
    elif (def1 in NUMERIC_TYPES) and (def2 in NUMERIC_TYPES):
        return NUMERIC_TYPES.find(def1) <= NUMERIC_TYPES.find(def2)

    elif def2.startswith("L"):
        if def1.startswith("L"):
            return find_javaclass(def2[1:-1]).isAssignableFrom(find_javaclass(def1[1:-1]))
        elif def1.startswith("["):
            return def2 in ARRAY_CONVERSIONS
    elif def2.startswith("["):
            return (def2[1] not in PRIMITIVE_TYPES and
                    def1.startswith("[") and
                    better_overload_arg(def1[1:], def2[1:], type(None)))

    return False


# Trigger a simple native crash, for use when testing logging.
def crash():
    cdef char *s = NULL
    print(s)

# Trigger a CheckJNI crash, for use when testing logging.
def crash_jni():
    cdef JNIEnv *j_env = get_jnienv()
    cdef jobject ref = j_env[0].FindClass(j_env, "java/lang/String")  # This is a local ref,
    j_env[0].DeleteGlobalRef(j_env, ref)                              # so this is invalid.


def plural(n, singular, plural=None):
    if plural is None:
        plural = singular + "s"
    return f"{n} {singular if (n == 1) else plural}"
