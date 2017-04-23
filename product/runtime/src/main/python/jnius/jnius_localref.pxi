from libc.stdint cimport uintptr_t

# TODO base both on JNIRef, which would contain the common behaviour (including __nonzero__,
# __repr__ and telem), and facilitate the JNI interface layer mentioned in jni.pxi.

# FIXME should be called GlobalRef
cdef class LocalRef(object):
    cdef jobject obj

    def __init__(self):
        telem[self.__class__.__name__] += 1

    def __dealloc__(self):
        cdef JNIEnv *j_env
        if self.obj != NULL:
            j_env = get_jnienv()
            j_env[0].DeleteGlobalRef(j_env, self.obj)
        self.obj = NULL
        telem[self.__class__.__name__] -= 1

    # FIXME use same approach as LocalActualRef
    cdef void create(self, JNIEnv *env, jobject obj):
        self.obj = env[0].NewGlobalRef(env, obj)

    def __repr__(self):
        return '<LocalRef obj=0x{0:x} at 0x{1:x}>'.format(
            <uintptr_t>self.obj, id(self))

    def __nonzero__(self):
        return self.obj != NULL


# FIXME use same approach as LocalActualRef
cdef LocalRef create_local_ref(JNIEnv *env, jobject obj):
    cdef LocalRef ret = LocalRef()
    ret.create(env, obj)
    return ret


# FIXME should be called LocalRef. Named to facilitate future search and replace.
cdef class LocalActualRef(object):
    # It's safe to store j_env, as long as the LocalActualRef isn't kept beyond the thread detach
    # or Java "native" method return.
    cdef JNIEnv *env
    cdef jobject obj

    def __init__(self):
        telem[self.__class__.__name__] += 1

    # Constructors can't take C pointer arguments
    @staticmethod
    cdef LocalActualRef create(JNIEnv *env, jobject obj):
        cdef LocalActualRef lr = LocalActualRef()
        lr.env = env
        lr.obj = obj
        return lr

    def __dealloc__(self):
        if self.obj:
            self.env[0].DeleteLocalRef(self.env, self.obj)
        self.obj = NULL
        telem[self.__class__.__name__] -= 1

    cdef LocalRef global_ref(self):
        return create_local_ref(self.env, self.obj)

    def __repr__(self):
        return '<LocalActualRef obj=0x{0:x} at 0x{1:x}>'.format(
            <uintptr_t>self.obj, id(self))

    def __nonzero__(self):
        return self.obj != NULL
