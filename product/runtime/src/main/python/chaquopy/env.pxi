# TODO create base class JNIRef, which would contain the common behaviour (including __nonzero__,
# __repr__ and telem), and facilitate the higher-level JNI interface layer.

# FIXME should be called GlobalRef
cdef class LocalRef(object):
    # Member variables declared in .pxd

    def __init__(self):
        telem[self.__class__.__name__] += 1

    def __dealloc__(self):
        cdef JNIEnv *j_env
        if self.obj != NULL:
            j_env = get_jnienv()
            j_env[0].DeleteGlobalRef(j_env, self.obj)
        self.obj = NULL
        telem[self.__class__.__name__] -= 1

    # Constructors can't take C pointer arguments
    @staticmethod
    cdef LocalRef create(JNIEnv *env, jobject obj):
        cdef LocalRef gr = LocalRef()
        gr.obj = env[0].NewGlobalRef(env, obj)
        return gr

    def __repr__(self):
        return '<LocalRef obj=0x{0:x} at 0x{1:x}>'.format(
            <uintptr_t>self.obj, id(self))

    def __nonzero__(self):
        return self.obj != NULL


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
        return LocalRef.create(self.env, self.obj)

    def __repr__(self):
        return '<LocalActualRef obj=0x{0:x} at 0x{1:x}>'.format(
            <uintptr_t>self.obj, id(self))

    def __nonzero__(self):
        return self.obj != NULL
