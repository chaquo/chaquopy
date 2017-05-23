# TODO #5176 expand and use more widely
cdef class CQPEnv(object):
    """Friendlier interface to JNIEnv"""

    cdef JNIEnv *j_env

    def __init__(self):
        self.j_env = get_jnienv()

    cpdef LocalRef FindClass(self, name):
        jniname = str_for_c(name.replace('.', '/'))
        result = self.adopt(self.j_env[0].FindClass(self.j_env, jniname))
        if not result:
            self.expect_exception(f"FindClass failed for {name}")
        return result

    def expect_exception(self, msg):
        expect_exception(self.j_env, msg)

    def check_exception(self):
        check_exception(self.j_env)

    cdef LocalRef adopt(self, jobject j_obj):
        return LocalRef.adopt(self.j_env, j_obj)


cdef class JNIRef(object):
    # Member variables declared in .pxd

    def __init__(self):
        telem[self.__class__.__name__] += 1

    def __dealloc__(self):
        telem[self.__class__.__name__] -= 1

    def __repr__(self):
        return f'<{self.__class__.__name__} obj=0x{<uintptr_t>self.obj:x}>'

    def __nonzero__(self):      # Python 2 name
        return self.obj != NULL
    def __bool__(self):         # Python 3 name
        return self.obj != NULL

    cdef GlobalRef global_ref(self):
        raise NotImplementedError()

    cdef jobject return_ref(self, JNIEnv *env):
        """Returns a new local reference suitable for returning from a `native` method or otherwise
        outliving the JNIRef object."""
        if self:
            return env[0].NewLocalRef(env, self.obj)
        else:
            return NULL


cdef class GlobalRef(object):
    @staticmethod
    cdef GlobalRef create(JNIEnv *env, jobject obj):
        cdef GlobalRef gr = GlobalRef()
        if obj:
            gr.obj = env[0].NewGlobalRef(env, obj)
        return gr

    def __dealloc__(self):
        cdef JNIEnv *j_env
        if self.obj:
            j_env = get_jnienv()
            j_env[0].DeleteGlobalRef(j_env, self.obj)
        self.obj = NULL
        # The __dealloc__() method of the superclass will be called automatically.

    cdef GlobalRef global_ref(self):
        return self


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

    cdef GlobalRef global_ref(self):
        return GlobalRef.create(self.env, self.obj)
