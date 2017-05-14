cdef class JNIRef(object):
    # Member variables declared in .pxd

    def __init__(self):
        telem[self.__class__.__name__] += 1

    def __dealloc__(self):
        telem[self.__class__.__name__] -= 1

    def __repr__(self):
        return f'<{self.__class__.__name__} obj=0x{<uintptr_t>self.obj:x}>'

    def __nonzero__(self):
        return self.obj != NULL

    cdef GlobalRef global_ref(self):
        if isinstance(self, GlobalRef):
            return self
        else:
            return GlobalRef.create((<LocalRef?>self).env, self.obj)

    cdef jobject return_ref(self, JNIEnv *env):
        """Returns a new local reference suitable for returning from a `native` method.
        """
        if self:
            return env[0].NewLocalRef(env, self.obj)
        else:
            return NULL


cdef class GlobalRef(object):
    def __dealloc__(self):
        cdef JNIEnv *j_env
        if self.obj:
            j_env = get_jnienv()
            j_env[0].DeleteGlobalRef(j_env, self.obj)
        self.obj = NULL
        # The __dealloc__() method of the superclass will be called automatically.

    @staticmethod
    cdef GlobalRef create(JNIEnv *env, jobject obj):
        cdef GlobalRef gr = GlobalRef()
        if obj:
            gr.obj = env[0].NewGlobalRef(env, obj)
        return gr


cdef class LocalRef(JNIRef):
    # Member variables declared in .pxd

    @staticmethod
    cdef LocalRef create(JNIEnv *env, jobject obj):
        return LocalRef.adopt(env,
                              env[0].NewLocalRef(env, obj) if obj else NULL)

    @staticmethod
    cdef LocalRef adopt(JNIEnv *env, jobject obj):
        cdef LocalRef lr = LocalRef()
        lr.env = env
        lr.obj = obj
        return lr

    def __dealloc__(self):
        if self.obj:
            self.env[0].DeleteLocalRef(self.env, self.obj)
        self.obj = NULL
        # The __dealloc__() method of the superclass will be called automatically.
