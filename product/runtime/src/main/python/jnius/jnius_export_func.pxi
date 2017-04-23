from cpython.version cimport PY_MAJOR_VERSION

def cast(destclass, obj):
    cdef JavaClass jc
    cdef JavaClass jobj = obj
    from .reflect import autoclass
    if (PY_MAJOR_VERSION < 3 and isinstance(destclass, basestring)) or \
          (PY_MAJOR_VERSION >=3 and isinstance(destclass, str)):
        jc = autoclass(destclass)(noinstance=True)
    else:
        jc = destclass(noinstance=True)
    jc.instanciate_from(jobj.j_self)
    return jc

def find_javaclass(namestr):
    """Returns the java.lang.Class proxy object corresponding to the given fully-qualified class
    name. Either '.' or '/' notation may be used. May raise any of the Java exceptions listed
    at https://docs.oracle.com/javase/8/docs/technotes/guides/jni/spec/functions.html#FindClass
    """
    namestr = namestr.replace('.', '/')
    cdef bytes name = str_for_c(namestr)
    from .reflect import Class
    cdef JavaClass cls
    cdef jclass jc
    cdef JNIEnv *j_env = get_jnienv()

    # FIXME all other uses of FindClass need to be guarded with expect_exception as well (see
    # note on exceptions in jni.pxi)
    jc = j_env[0].FindClass(j_env, name)
    if jc == NULL:
        expect_exception(j_env, f"FindClass failed for {name}")

    cls = Class(noinstance=True)
    cls.instanciate_from(create_local_ref(j_env, jc))
    j_env[0].DeleteLocalRef(j_env, jc)
    return cls

