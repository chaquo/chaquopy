# TODO create base class JNIRef, which would contain the common behaviour (including __nonzero__,
# __repr__ and telem), and facilitate the higher-level JNI interface layer.

cdef class GlobalRef(object):
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
    cdef GlobalRef create(JNIEnv *env, jobject obj):
        cdef GlobalRef gr = GlobalRef()
        gr.obj = env[0].NewGlobalRef(env, obj)
        return gr

    def __repr__(self):
        return '<GlobalRef obj=0x{0:x} at 0x{1:x}>'.format(
            <uintptr_t>self.obj, id(self))

    def __nonzero__(self):
        return self.obj != NULL


cdef class LocalRef(object):
    # It's safe to store j_env, as long as the LocalRef isn't kept beyond the thread detach
    # or Java "native" method return.
    cdef JNIEnv *env
    cdef jobject obj

    def __init__(self):
        telem[self.__class__.__name__] += 1

    # Constructors can't take C pointer arguments
    @staticmethod
    cdef LocalRef wrap(JNIEnv *env, jobject obj):
        cdef LocalRef lr = LocalRef()
        lr.env = env
        lr.obj = obj
        return lr

    def __dealloc__(self):
        if self.obj:
            self.env[0].DeleteLocalRef(self.env, self.obj)
        self.obj = NULL
        telem[self.__class__.__name__] -= 1

    cdef GlobalRef global_ref(self):
        return GlobalRef.create(self.env, self.obj)

    def __repr__(self):
        return '<LocalRef obj=0x{0:x} at 0x{1:x}>'.format(
            <uintptr_t>self.obj, id(self))

    def __nonzero__(self):
        return self.obj != NULL
