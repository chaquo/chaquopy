from collections import OrderedDict


global_classes = OrderedDict()

# Schedules the the given class to be added to the module dictionary, under its simple name,
# once bootstrap is complete.
def global_class(full_name, **kwargs):
    if "Class" in globals():
        raise Exception(f"global_class('{full_name}') called after bootstrap complete")

    # Because kwargs may vary, global_class can only be used once per class. Also, because the
    # simple class name becomes an attribute of this module, that must be unique too.
    simple_name = full_name.rpartition(".")[2]
    assert simple_name not in global_classes, full_name
    global_classes[simple_name] = (full_name, kwargs)

    # globals() is non-trivial in Cython, so it's better for performance-critical code
    # elsewhere to be checking `is not None` rather than `in globals()`.
    globals()[simple_name] = None


def load_global_classes():
    g = globals()
    for simple_name, (full_name, kwargs) in six.iteritems(global_classes):
        assert full_name not in jclass_cache, full_name  # See comment at Throwable in exception.pxi
        g[simple_name] = jclass(full_name, **kwargs)
    global_classes.clear()


# I considered whether to make `cast` aliases clearly distinguishable from plain objects, by
# generalizing `NoneCast` to `Cast`, and giving it a `repr` of `cast('<jni-signature>',
# repr(<underlying-object>))`. However, this would be a major change for no clear benefit.
def cast(cls, obj):
    """Returns a view of the given object as the given class. The class must be one created by
    :any:`jclass` or :any:`jarray`, or a JNI type signature for a class or array. The object
    must either be assignable to the given class, or `None` (representing Java `null`),
    otherwise `TypeError` will be raised.

    Situations where this could be useful are the same as those where you might use the Java
    cast syntax `(ClassName)obj`. By changing the apparent type of an object:

    * Different members may be visible on the object.
    * A different overload may be chosen when passing the object to a method.
    """
    sig = java.jni_sig(cls)
    if sig[0] not in "L[":
        raise TypeError(f"{type(cls).__name__} object does not specify a Java class or array type")

    if obj is None or isinstance(obj, NoneCast):
        with class_lock:
            return none_casts[sig]
    else:
        if isinstance(obj, JavaObject):
            instance = obj._chaquopy_this
        else:
            raise TypeError(f"{type(obj).__name__} object is not a Java object or array")
        return jclass(sig)(instance=instance)


class NoneCast(object):
    def __repr__(self):
        return f"cast('{self.sig}', None)"

    def __nonzero__(self):      # Python 2 name
        return False
    def __bool__(self):         # Python 3 name
        return False


class none_cast_dict(dict):
    # Use a different subclass for each type, so overload resolution can be cached.
    def __missing__(self, sig):
        obj = type(str("NoneCast_" + sig),
                   (NoneCast,),
                   {"sig": sig})()
        self[sig] = obj
        return obj

none_casts = none_cast_dict()


def cls_fullname(cls):
    module = cls.__module__
    return f"{(module + '.') if module else ''}{cls.__name__}"


cdef str_for_c(s):
    if isinstance(s, unicode):
        return s.encode('utf-8')
    else:
        assert isinstance(s, bytes)
        return s


# Hide difference between unicode and byte strings to make tests consistent between Python 2
# and 3.
def str_repr(s):
    result = repr(s)
    if isinstance(s, unicode) and result.startswith("u"):
        result = result[1:]
    return result


cdef jmethodID mid_getName = NULL

# To avoid infinite recursion, this function must not use anything which could call
# klass_sig itself, including any jclass proxy methods.
def klass_sig(CQPEnv env, JNIRef j_cls):
    global mid_getName
    if not mid_getName:
        j_Class = env.FindClass("java.lang.Class")
        mid_getName = env.GetMethodID(j_Class, 'getName', '()Ljava/lang/String;')

    j_name = env.adopt(env.j_env[0].CallObjectMethod(env.j_env, j_cls.obj, mid_getName))
    if not j_name:
        env.ExceptionClear()
        raise Exception("getName failed")
    return java.name_to_sig(j2p_string(env.j_env, j_name))


def object_sig(CQPEnv env, JNIRef j_obj):
    return klass_sig(env, env.GetObjectClass(j_obj))


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
    # All Python iterable types are considered applicable to all array types. (p2j would
    # type-check the values, possibly leading to incorrect overload caching.)
    if assignable_to_array(r, arg):
        return True
    try:
        p2j(env, r, arg, autobox)
        return True
    except TypeError:
        return False


def better_overload(CQPEnv env, JavaMethod jm1, JavaMethod jm2, actual_types, *, varargs):
    """Returns whether jm1 is an equal or better match than jm2 for the given actual parameter
    types. This is based on JLS 15.12.2.5. "Choosing the Most Specific Method" and JLS 4.10.
    "Subtyping".
    """
    defs1, defs2 = jm1.args_sig, jm2.args_sig

    if varargs:
        if not actual_types:
            # No arguments were given, so the definitions must both be of the form (X...). Give
            # a fake argument so they can be compared.
            actual_types = [type(None)]
        defs1 = extend_varargs(defs1, len(actual_types))
        defs2 = extend_varargs(defs2, len(actual_types))

    return (len(defs1) == len(defs2) and
            all([better_overload_arg(env, d1, d2, at)
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
def better_overload_arg(CQPEnv env, def1, def2, actual_type):
    if def2 == def1:
        return True

    # To avoid data loss, we prefer to treat a Python int or float as the largest of the
    # corresponding Java types.
    elif issubclass(actual_type, six.integer_types) and (def1 in INT_TYPES) and (def2 in INT_TYPES):
        return dict_index(INT_TYPES, def1) <= dict_index(INT_TYPES, def2)
    elif issubclass(actual_type, float) and (def1 in FLOAT_TYPES) and (def2 in FLOAT_TYPES):
        return dict_index(FLOAT_TYPES, def1) <= dict_index(FLOAT_TYPES, def2)

    # Similarly, we prefer to treat a Python string as a Java String rather than a character.
    # (Its length cannot be taken into account: see note above about caching.)
    elif issubclass(actual_type, six.string_types) and \
         def2 in ["C", "Ljava/lang/Character;"] and \
         env.IsAssignableFrom(env.FindClass("Ljava/lang/String;"), env.FindClass(def1)):
        return True

    # Otherwise we prefer the smallest (i.e. most specific) Java type. This includes the case
    # of passing a Python int where float and double overloads exist: the float overload will
    # be called, just like in Java.
    elif (def1 in NUMERIC_TYPES) and (def2 in NUMERIC_TYPES):
        return dict_index(NUMERIC_TYPES, def1) >= dict_index(NUMERIC_TYPES, def2)

    elif def2.startswith("L"):
        if def1.startswith("L"):
            return env.IsAssignableFrom(env.FindClass(def1), env.FindClass(def2))
        elif def1.startswith("["):
            return def2 in ARRAY_CONVERSIONS
    elif def2.startswith("["):
            return (def2[1] not in PRIMITIVE_TYPES and
                    def1.startswith("[") and
                    better_overload_arg(env, def1[1:], def2[1:], type(None)))

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
