from libc.stdint cimport uintptr_t
from libc.stdlib cimport abort


global_classes = OrderedDict()

# Schedules the the given class to be added to the module dictionary, under its simple name,
# once bootstrap is complete.
cdef global_class(full_name, cls_dict=None):
    if "Class" in globals():
        raise Exception(f"global_class('{full_name}') called after bootstrap complete")

    # Because kwargs may vary, global_class can only be used once per class. Also, because the
    # simple class name becomes an attribute of this module, that must be unique too.
    simple_name = full_name.rpartition(".")[2]
    assert simple_name not in global_classes, full_name
    global_classes[simple_name] = (full_name, cls_dict)

    # globals() is non-trivial in Cython, so it's better for performance-critical code
    # elsewhere to be checking `is not None` rather than `in globals()`.
    globals()[simple_name] = None


cdef load_global_classes():
    g = globals()
    for simple_name, (full_name, cls_dict) in six.iteritems(global_classes):
        g[simple_name] = jclass(full_name, cls_dict)
    global_classes.clear()


# I considered whether to make `cast` aliases clearly distinguishable from plain objects, by
# generalizing `NoneCast` to `Cast`, and giving it a `repr` of `cast('<jni-signature>',
# repr(<underlying-object>))`. However, this would be a major change for no clear benefit.
cpdef cast(cls, obj):
    """Returns a view of the given object as the given class. The class must be one created by
    :any:`jclass` or :any:`jarray`, or a JNI type signature for a class or array. The object
    must either be assignable to the given class, or `None` (representing Java `null`),
    otherwise `TypeError` will be raised.

    Situations where this could be useful are the same as those where you might use the Java
    cast syntax `(ClassName)obj`. By changing the apparent type of an object:

    * Different members may be visible on the object.
    * A different overload may be chosen when passing the object to a method.
    """
    sig = jni_sig(cls)
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


cdef cls_fullname(cls):
    module = cls.__module__
    return f"{(module + '.') if module else ''}{cls.__name__}"


cdef str_for_c(s):
    if isinstance(s, unicode):
        return s.encode('utf-8')
    else:
        assert isinstance(s, bytes)
        return s


# cpdef because it's called from primitive.py.
cpdef native_str(s):
    if isinstance(s, unicode):
        return s.encode("utf-8") if six.PY2 else s
    else:
        assert isinstance(s, bytes)
        return s if six.PY2 else s.decode("utf-8")


# Trigger a simple native crash, for use when testing logging. Also called by license enforcement,
# where we want to make sure it's reported as a crash in both the logcat and the UI, otherwise the
# back-stack might just be recreated in a new process and it wouldn't be obvious what happened.
# abort(2) and SIGKILL aren't good enough because they exit silently on API level 26.
#
# The following generates a SIGSEGV as expected on API level 23, but on API level 26 it generates a
# SIGSYS with the error "seccomp prevented call to disallowed x86 system call 7", and Chrome.apk at
# the top of the stack. None of that makes any sense to me (maybe it's because it's an emulator),
# but at least it's reliable.
cpdef crash():
    # Avoid C compiler null pointer optimizations in release builds, which on API level 26 actually
    # caused us to not crash and print a random number instead.
    cdef int *p = <int*><uintptr_t> int("0")
    print(p[0])
    abort()  # Just in case that didn't work.


# Trigger a CheckJNI crash, for use when testing logging.
cpdef crash_jni():
    cdef JNIEnv *j_env = get_jnienv()
    cdef jobject ref = j_env[0].FindClass(j_env, "java/lang/String")  # This is a local ref,
    j_env[0].DeleteGlobalRef(j_env, ref)                              # so this is invalid.


cdef plural(n, singular, plural=None):
    if plural is None:
        plural = singular + "s"
    return f"{n} {singular if (n == 1) else plural}"
