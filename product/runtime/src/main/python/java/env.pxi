from cpython.object cimport Py_EQ, Py_NE


# Friendlier interface to JNIEnv:
#   * Checks for and raises Java exceptions.
#   * Uses JNIRef everywhere.
#   * Where JNIEnv returns a jboolean, CQPEnv returns a Python bool.
#   * Where JNIEnv accepts a jchar, CQPEnv accepts a single-character Python Unicode
#     or byte string, checking that the character is in the BMP. Where JNIEnv returns a jchar,
#     CQPEnv returns a Python Unicode string.
#   * Where JNIEnv accepts a char*, CQPEnv accepts a Python Unicode and byte string,
#
cdef class CQPEnv(object):
    cdef JNIEnv *j_env

    def __init__(self, get=True):
        if get:
            self.j_env = get_jnienv()

    @staticmethod
    cdef CQPEnv wrap(JNIEnv *j_env):
        env = CQPEnv(get=False)
        env.j_env = j_env
        return env

    # All common notations may be used, including '.' or '/' to separate package names, and
    # optional "L" and ";" at start and end. Use a leading "[" for array types.
    #
    # When not running within the context of a Java `native` method (e.g. in a Python-created
    # thread), JNI FindClass uses the "system" ClassLoader, which can only see standard library
    # classes on Android. So once bootstrap is complete, we cache the correct ClassLoader and
    # use it directly from then on.
    #
    # ClassLoader.loadClass is recommended at
    # https://developer.android.com/training/articles/perf-jni.html#faq_FindClass, but it's not
    # a drop-in replacement for FindClass because it doesn't work with array classes
    # (http://bugs.java.com/view_bug.do?bug_id=6500212). So we use Class.forName instead.
    cdef JNIRef FindClass(self, cls):
        global ClassNotFoundException, NoClassDefFoundError
        name = cls if isinstance(cls, six.string_types) else java.jni_sig(cls)
        if name.startswith("L") and name.endswith(";"):
            name = name[1:-1]

        try:
            if not mid_forName:    # Bootstrap not complete (see set_jvm)
                name = name.replace(".", "/")
                result = self.adopt(self.j_env[0].FindClass(self.j_env, str_for_c(name)))
                if result:
                    return result
                else:
                    # Java SE 8 throws NoClassDefFoundError like the JNI spec says, but Android 6
                    # throws ClassNotFoundException.
                    self.expect_exception(f"FindClass failed for {name}")
            else:
                name = name.replace("/", ".")
                j_name = p2j_string(self.j_env, name)
                # On Dalvik (but not ART), when CallStaticObjectMethod throws an exception, it
                # doesn't return NULL. I don't know what value it's returning, but passing it
                # to DeleteLocalRef causes a crash, so we must not adopt it until after we've
                # checked for exceptions.
                j_result = self.j_env[0].CallStaticObjectMethod(
                    self.j_env, (<JNIRef?>Class._chaquopy_j_klass).obj, mid_forName,
                    j_name.obj, JNI_FALSE, j_class_loader.obj)
                self.check_exception()  # throws ClassNotFoundException
                return self.adopt(j_result)
        except Exception as e:
            # Putting ClassNotFoundException directly in an `except` clause would cause any
            # other exception to be hidden by a NameError if bootstrap isn't complete.
            if (ClassNotFoundException is not None) and isinstance(e, ClassNotFoundException):
                ncdfe = NoClassDefFoundError(e.getMessage())
                ncdfe.setStackTrace(e.getStackTrace())
                raise ncdfe
            else:
                raise

    cdef IsAssignableFrom(self, JNIRef j_klass1, JNIRef j_klass2):
        return bool(self.j_env[0].IsAssignableFrom(self.j_env, j_klass1.obj, j_klass2.obj))

    cdef LocalRef ExceptionOccurred(self):
        return self.adopt(self.j_env[0].ExceptionOccurred(self.j_env))

    cdef ExceptionClear(self):
        self.j_env[0].ExceptionClear(self.j_env)

    cdef IsSameObject(self, JNIRef ref1, JNIRef ref2):
        return bool(self.j_env[0].IsSameObject(self.j_env, ref1.obj, ref2.obj))

    cdef LocalRef NewObjectA(self, JNIRef j_klass, jmethodID mid, jvalue *args):
        cdef jobject result
        with nogil:
            result = self.j_env[0].NewObjectA(self.j_env, j_klass.obj, mid, args)
        self.check_exception()
        return self.adopt(result)

    cdef LocalRef GetObjectClass(self, JNIRef obj):
        return self.adopt(self.j_env[0].GetObjectClass(self.j_env, obj.obj))

    cdef IsInstanceOf(self, JNIRef obj, JNIRef j_klass):
        return bool(self.j_env[0].IsInstanceOf(self.j_env, obj.obj, j_klass.obj))

    cdef jmethodID GetMethodID(self, JNIRef j_klass, name, definition) except NULL:
        cdef jmethodID result = self.j_env[0].GetMethodID \
            (self.j_env, j_klass.obj, str_for_c(name), str_for_c(definition))
        if result == NULL:
            self.expect_exception(f'GetMethodID failed for {name}, {definition}')
        return result

    cdef LocalRef CallObjectMethodA(self, JNIRef this, jmethodID mid, jvalue *args):
        cdef jobject result
        with nogil:
            result = self.j_env[0].CallObjectMethodA(self.j_env, this.obj, mid, args)
        self.check_exception()
        return self.adopt(result)
    cdef CallBooleanMethodA(self, JNIRef this, jmethodID mid, jvalue *args):
        cdef jboolean result
        with nogil:
            result = self.j_env[0].CallBooleanMethodA(self.j_env, this.obj, mid, args)
        self.check_exception()
        return bool(result)
    cdef CallByteMethodA(self, JNIRef this, jmethodID mid, jvalue *args):
        cdef jbyte result
        with nogil:
            result = self.j_env[0].CallByteMethodA(self.j_env, this.obj, mid, args)
        self.check_exception()
        return result
    cdef CallCharMethodA(self, JNIRef this, jmethodID mid, jvalue *args):
        cdef jchar result
        with nogil:
            result = self.j_env[0].CallCharMethodA(self.j_env, this.obj, mid, args)
        self.check_exception()
        return six.unichr(result)
    cdef CallShortMethodA(self, JNIRef this, jmethodID mid, jvalue *args):
        cdef jshort result
        with nogil:
            result = self.j_env[0].CallShortMethodA(self.j_env, this.obj, mid, args)
        self.check_exception()
        return result
    cdef CallIntMethodA(self, JNIRef this, jmethodID mid, jvalue *args):
        cdef jint result
        with nogil:
            result = self.j_env[0].CallIntMethodA(self.j_env, this.obj, mid, args)
        self.check_exception()
        return result
    cdef CallLongMethodA(self, JNIRef this, jmethodID mid, jvalue *args):
        cdef jlong result
        with nogil:
            result = self.j_env[0].CallLongMethodA(self.j_env, this.obj, mid, args)
        self.check_exception()
        return result
    cdef CallFloatMethodA(self, JNIRef this, jmethodID mid, jvalue *args):
        cdef jfloat result
        with nogil:
            result = self.j_env[0].CallFloatMethodA(self.j_env, this.obj, mid, args)
        self.check_exception()
        return result
    cdef CallDoubleMethodA(self, JNIRef this, jmethodID mid, jvalue *args):
        cdef jdouble result
        with nogil:
            result = self.j_env[0].CallDoubleMethodA(self.j_env, this.obj, mid, args)
        self.check_exception()
        return result
    cdef CallVoidMethodA(self, JNIRef this, jmethodID mid, jvalue *args):
        with nogil:
            self.j_env[0].CallVoidMethodA(self.j_env, this.obj, mid, args)
        self.check_exception()

    cdef LocalRef CallNonvirtualObjectMethodA(self, JNIRef this, JNIRef j_klass, jmethodID mid, jvalue *args):
        cdef jobject result
        with nogil:
            result = self.j_env[0].CallNonvirtualObjectMethodA(self.j_env, this.obj, j_klass.obj, mid, args)
        self.check_exception()
        return self.adopt(result)
    cdef CallNonvirtualBooleanMethodA(self, JNIRef this, JNIRef j_klass, jmethodID mid, jvalue *args):
        cdef jboolean result
        with nogil:
            result = self.j_env[0].CallNonvirtualBooleanMethodA(self.j_env, this.obj, j_klass.obj, mid, args)
        self.check_exception()
        return bool(result)
    cdef CallNonvirtualByteMethodA(self, JNIRef this, JNIRef j_klass, jmethodID mid, jvalue *args):
        cdef jbyte result
        with nogil:
            result = self.j_env[0].CallNonvirtualByteMethodA(self.j_env, this.obj, j_klass.obj, mid, args)
        self.check_exception()
        return result
    cdef CallNonvirtualCharMethodA(self, JNIRef this, JNIRef j_klass, jmethodID mid, jvalue *args):
        cdef jchar result
        with nogil:
            result = self.j_env[0].CallNonvirtualCharMethodA(self.j_env, this.obj, j_klass.obj, mid, args)
        self.check_exception()
        return six.unichr(result)
    cdef CallNonvirtualShortMethodA(self, JNIRef this, JNIRef j_klass, jmethodID mid, jvalue *args):
        cdef jshort result
        with nogil:
            result = self.j_env[0].CallNonvirtualShortMethodA(self.j_env, this.obj, j_klass.obj, mid, args)
        self.check_exception()
        return result
    cdef CallNonvirtualIntMethodA(self, JNIRef this, JNIRef j_klass, jmethodID mid, jvalue *args):
        cdef jint result
        with nogil:
            result = self.j_env[0].CallNonvirtualIntMethodA(self.j_env, this.obj, j_klass.obj, mid, args)
        self.check_exception()
        return result
    cdef CallNonvirtualLongMethodA(self, JNIRef this, JNIRef j_klass, jmethodID mid, jvalue *args):
        cdef jlong result
        with nogil:
            result = self.j_env[0].CallNonvirtualLongMethodA(self.j_env, this.obj, j_klass.obj, mid, args)
        self.check_exception()
        return result
    cdef CallNonvirtualFloatMethodA(self, JNIRef this, JNIRef j_klass, jmethodID mid, jvalue *args):
        cdef jfloat result
        with nogil:
            result = self.j_env[0].CallNonvirtualFloatMethodA(self.j_env, this.obj, j_klass.obj, mid, args)
        self.check_exception()
        return result
    cdef CallNonvirtualDoubleMethodA(self, JNIRef this, JNIRef j_klass, jmethodID mid, jvalue *args):
        cdef jdouble result
        with nogil:
            result = self.j_env[0].CallNonvirtualDoubleMethodA(self.j_env, this.obj, j_klass.obj, mid, args)
        self.check_exception()
        return result
    cdef CallNonvirtualVoidMethodA(self, JNIRef this, JNIRef j_klass, jmethodID mid, jvalue *args):
        with nogil:
            self.j_env[0].CallNonvirtualVoidMethodA(self.j_env, this.obj, j_klass.obj, mid, args)
        self.check_exception()

    cdef jfieldID GetFieldID(self, JNIRef j_klass, name, definition) except NULL:
        cdef jfieldID result = self.j_env[0].GetFieldID \
            (self.j_env, j_klass.obj, str_for_c(name), str_for_c(definition))
        if result == NULL:
            self.expect_exception(f'GetFieldID failed for {name}, {definition}')
        return result

    cdef jmethodID GetStaticMethodID(self, JNIRef j_klass, name, definition) except NULL:
        cdef jmethodID result = self.j_env[0].GetStaticMethodID \
            (self.j_env, j_klass.obj, str_for_c(name), str_for_c(definition))
        if result == NULL:
            self.expect_exception(f'GetStaticMethodID failed for {name}, {definition}')
        return result

    cdef LocalRef CallStaticObjectMethodA(self, JNIRef j_klass, jmethodID mid, jvalue *args):
        cdef jobject result
        with nogil:
            result = self.j_env[0].CallStaticObjectMethodA(self.j_env, j_klass.obj, mid, args)
        self.check_exception()
        return self.adopt(result)
    cdef CallStaticBooleanMethodA(self, JNIRef j_klass, jmethodID mid, jvalue *args):
        cdef jboolean result
        with nogil:
            result = self.j_env[0].CallStaticBooleanMethodA(self.j_env, j_klass.obj, mid, args)
        self.check_exception()
        return bool(result)
    cdef CallStaticByteMethodA(self, JNIRef j_klass, jmethodID mid, jvalue *args):
        cdef jbyte result
        with nogil:
            result = self.j_env[0].CallStaticByteMethodA(self.j_env, j_klass.obj, mid, args)
        self.check_exception()
        return result
    cdef CallStaticCharMethodA(self, JNIRef j_klass, jmethodID mid, jvalue *args):
        cdef jchar result
        with nogil:
            result = self.j_env[0].CallStaticCharMethodA(self.j_env, j_klass.obj, mid, args)
        self.check_exception()
        return six.unichr(result)
    cdef CallStaticShortMethodA(self, JNIRef j_klass, jmethodID mid, jvalue *args):
        cdef jshort result
        with nogil:
            result = self.j_env[0].CallStaticShortMethodA(self.j_env, j_klass.obj, mid, args)
        self.check_exception()
        return result
    cdef CallStaticIntMethodA(self, JNIRef j_klass, jmethodID mid, jvalue *args):
        cdef jint result
        with nogil:
            result = self.j_env[0].CallStaticIntMethodA(self.j_env, j_klass.obj, mid, args)
        self.check_exception()
        return result
    cdef CallStaticLongMethodA(self, JNIRef j_klass, jmethodID mid, jvalue *args):
        cdef jlong result
        with nogil:
            result = self.j_env[0].CallStaticLongMethodA(self.j_env, j_klass.obj, mid, args)
        self.check_exception()
        return result
    cdef CallStaticFloatMethodA(self, JNIRef j_klass, jmethodID mid, jvalue *args):
        cdef jfloat result
        with nogil:
            result = self.j_env[0].CallStaticFloatMethodA(self.j_env, j_klass.obj, mid, args)
        self.check_exception()
        return result
    cdef CallStaticDoubleMethodA(self, JNIRef j_klass, jmethodID mid, jvalue *args):
        cdef jdouble result
        with nogil:
            result = self.j_env[0].CallStaticDoubleMethodA(self.j_env, j_klass.obj, mid, args)
        self.check_exception()
        return result
    cdef CallStaticVoidMethodA(self, JNIRef j_klass, jmethodID mid, jvalue *args):
        with nogil:
            self.j_env[0].CallStaticVoidMethodA(self.j_env, j_klass.obj, mid, args)
        self.check_exception()

    cdef jfieldID GetStaticFieldID(self, JNIRef j_klass, name, definition) except NULL:
        cdef jfieldID result = self.j_env[0].GetStaticFieldID \
            (self.j_env, j_klass.obj, str_for_c(name), str_for_c(definition))
        if result == NULL:
            self.expect_exception(f'GetStaticFieldID failed for {name}, {definition}')
        return result

    cdef GetArrayLength(self, JNIRef array):
        return self.j_env[0].GetArrayLength(self.j_env, array.obj)

    cdef LocalRef NewBooleanArray(self, length):
        return self.adopt_notnull(self.j_env[0].NewBooleanArray(self.j_env, length))
    cdef LocalRef NewByteArray(self, length):
        return self.adopt_notnull(self.j_env[0].NewByteArray(self.j_env, length))
    cdef LocalRef NewShortArray(self, length):
        return self.adopt_notnull(self.j_env[0].NewShortArray(self.j_env, length))
    cdef LocalRef NewIntArray(self, length):
        return self.adopt_notnull(self.j_env[0].NewIntArray(self.j_env, length))
    cdef LocalRef NewLongArray(self, length):
        return self.adopt_notnull(self.j_env[0].NewLongArray(self.j_env, length))
    cdef LocalRef NewFloatArray(self, length):
        return self.adopt_notnull(self.j_env[0].NewFloatArray(self.j_env, length))
    cdef LocalRef NewDoubleArray(self, length):
        return self.adopt_notnull(self.j_env[0].NewDoubleArray(self.j_env, length))
    cdef LocalRef NewCharArray(self, length):
        return self.adopt_notnull(self.j_env[0].NewCharArray(self.j_env, length))
    cdef LocalRef NewObjectArray(self, length, JNIRef j_klass):
        return self.adopt_notnull(self.j_env[0].NewObjectArray(self.j_env, length, j_klass.obj, NULL))

    cdef jbyte *GetByteArrayElements(self, JNIRef array):
        result = self.j_env[0].GetByteArrayElements(self.j_env, array.obj, NULL)
        if result == NULL:
            self.expect_exception("GetByteArrayElements failed")
        return result

    cdef void ReleaseByteArrayElements(self, JNIRef array, jbyte *elems, jint mode):
        self.j_env[0].ReleaseByteArrayElements(self.j_env, array.obj, elems, mode)

    # The primitive type Get...ArrayElement functions are not in the JNI, but are provided for
    # convenience.
    cdef GetBooleanArrayElement(self, JNIRef array, index):
        cdef jboolean j_value = 0
        self.j_env[0].GetBooleanArrayRegion(self.j_env, array.obj, index, 1, &j_value)
        self.check_exception()
        return bool(j_value)
    cdef GetByteArrayElement(self, JNIRef array, index):
        cdef jbyte j_value = 0
        self.j_env[0].GetByteArrayRegion(self.j_env, array.obj, index, 1, &j_value)
        self.check_exception()
        return j_value
    cdef GetShortArrayElement(self, JNIRef array, index):
        cdef jshort j_value = 0
        self.j_env[0].GetShortArrayRegion(self.j_env, array.obj, index, 1, &j_value)
        self.check_exception()
        return j_value
    cdef GetIntArrayElement(self, JNIRef array, index):
        cdef jint j_value = 0
        self.j_env[0].GetIntArrayRegion(self.j_env, array.obj, index, 1, &j_value)
        self.check_exception()
        return j_value
    cdef GetLongArrayElement(self, JNIRef array, index):
        cdef jlong j_value = 0
        self.j_env[0].GetLongArrayRegion(self.j_env, array.obj, index, 1, &j_value)
        self.check_exception()
        return j_value
    cdef GetFloatArrayElement(self, JNIRef array, index):
        cdef jfloat j_value = 0
        self.j_env[0].GetFloatArrayRegion(self.j_env, array.obj, index, 1, &j_value)
        self.check_exception()
        return j_value
    cdef GetDoubleArrayElement(self, JNIRef array, index):
        cdef double j_value = 0
        self.j_env[0].GetDoubleArrayRegion(self.j_env, array.obj, index, 1, &j_value)
        self.check_exception()
        return j_value
    cdef GetCharArrayElement(self, JNIRef array, index):
        cdef jchar j_value = 0
        self.j_env[0].GetCharArrayRegion(self.j_env, array.obj, index, 1, &j_value)
        self.check_exception()
        return six.unichr(j_value)
    cdef LocalRef GetObjectArrayElement(self, JNIRef array, index):
        result = self.adopt(self.j_env[0].GetObjectArrayElement(self.j_env, array.obj, index))
        self.check_exception()
        return result

    # The primitive type Set...ArrayElement functions are not in the JNI, but are provided for
    # convenience.
    cdef SetBooleanArrayElement(self, JNIRef array, index, value):
        cdef jboolean j_value = value
        self.j_env[0].SetBooleanArrayRegion(self.j_env, array.obj, index, 1, &j_value)
        self.check_exception()
    cdef SetByteArrayElement(self, JNIRef array, index, value):
        cdef jbyte j_value = value
        self.j_env[0].SetByteArrayRegion(self.j_env, array.obj, index, 1, &j_value)
        self.check_exception()
    cdef SetShortArrayElement(self, JNIRef array, index, value):
        cdef jshort j_value = value
        self.j_env[0].SetShortArrayRegion(self.j_env, array.obj, index, 1, &j_value)
        self.check_exception()
    cdef SetIntArrayElement(self, JNIRef array, index, value):
        cdef jint j_value = value
        self.j_env[0].SetIntArrayRegion(self.j_env, array.obj, index, 1, &j_value)
        self.check_exception()
    cdef SetLongArrayElement(self, JNIRef array, index, value):
        cdef jlong j_value = value
        self.j_env[0].SetLongArrayRegion(self.j_env, array.obj, index, 1, &j_value)
        self.check_exception()
    cdef SetFloatArrayElement(self, JNIRef array, index, value):
        check_range_float32(value)
        cdef jfloat j_value = value
        self.j_env[0].SetFloatArrayRegion(self.j_env, array.obj, index, 1, &j_value)
        self.check_exception()
    cdef SetDoubleArrayElement(self, JNIRef array, index, value):
        cdef jdouble j_value = value
        self.j_env[0].SetDoubleArrayRegion(self.j_env, array.obj, index, 1, &j_value)
        self.check_exception()
    cdef SetCharArrayElement(self, JNIRef array, index, value):
        check_range_char(value)
        cdef jchar j_value = ord(value)
        self.j_env[0].SetCharArrayRegion(self.j_env, array.obj, index, 1, &j_value)
        self.check_exception()
    cdef SetObjectArrayElement(self, JNIRef array, index, JNIRef value):
        self.j_env[0].SetObjectArrayElement(self.j_env, array.obj, index, value.obj)
        self.check_exception()

    cdef LocalRef adopt_notnull(self, jobject j_obj):
        if not j_obj:
            self.expect_exception("NULL object")
        return self.adopt(j_obj)

    cdef LocalRef adopt(self, jobject j_obj):
        return LocalRef.adopt(self.j_env, j_obj)

    cdef expect_exception(self, msg):
        self.check_exception()
        raise Exception(msg)

    cdef check_exception(self):
        check_exception(self.j_env)


cdef GlobalRef j_System
cdef jmethodID mid_identityHashCode = NULL

cdef class JNIRef(object):
    # Member variables declared in .pxd

    def __dealloc__(self):
        self.obj = NULL

    def __repr__(self):
        return f'<{type(self).__name__} obj=0x{<uintptr_t>self.obj:x}>'

    def __richcmp__(self, JNIRef other, int op):
        # Can't call __richcmp__ recursively for !=: Cython generates a Python-level call, but
        # it isn't exposed at the Python level.
        is_same = CQPEnv().IsSameObject(self, other)
        if op == Py_EQ:
            return is_same
        elif op == Py_NE:
            return not is_same
        else:
            raise NotImplementedError()

    # I've not seen any evidence that caching the hash code really helps performance, but it
    # reduces the risk of calling JNI functions in fragile situations such as when we have a
    # Java exception pending (see note at chaquopy_java.get_exception).
    def __hash__(self):
        if not self.hash_code:
            global j_System, mid_identityHashCode
            env = CQPEnv()
            if not j_System:
                j_System = env.FindClass("Ljava/lang/System;").global_ref()
                mid_identityHashCode = env.GetStaticMethodID \
                    (j_System, "identityHashCode", "(Ljava/lang/Object;)I")
            self.hash_code = env.j_env[0].CallStaticIntMethod \
                (env.j_env, j_System.obj, mid_identityHashCode, self.obj)
        return self.hash_code

    def __nonzero__(self):      # Python 2 name
        return self.obj != NULL
    def __bool__(self):         # Python 3 name
        return self.obj != NULL

    cdef GlobalRef global_ref(self):
        return GlobalRef.create(get_jnienv(), self.obj)

    cdef WeakRef weak_ref(self):
        return WeakRef.create(get_jnienv(), self.obj)

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
        gr = GlobalRef()
        if obj:
            gr.obj = env[0].NewGlobalRef(env, obj)
        return gr

    def __dealloc__(self):
        cdef JNIEnv *j_env
        if self.obj:
            j_env = get_jnienv()
            j_env[0].DeleteGlobalRef(j_env, self.obj)
        # The __dealloc__() method of the superclass will be called automatically.

    cdef GlobalRef global_ref(self):
        return self


cdef class LocalRef(JNIRef):
    # Member variables declared in .pxd

    @staticmethod
    cdef LocalRef create(JNIEnv *env, jobject obj):
        return LocalRef.adopt(env,
                              env[0].NewLocalRef(env, obj) if obj else NULL)

    # This should not be used for parameters of `native` methods: on Android, that causes the
    # warning "Attempt to remove non-JNI local reference". Use `LocalRef.create` instead.
    @staticmethod
    cdef LocalRef adopt(JNIEnv *env, jobject obj):
        lr = LocalRef()
        lr.env = env
        lr.obj = obj
        return lr

    def __dealloc__(self):
        if self.obj:
            self.env[0].DeleteLocalRef(self.env, self.obj)
        # The __dealloc__() method of the superclass will be called automatically.


cdef class WeakRef(JNIRef):
    @staticmethod
    cdef WeakRef create(JNIEnv *env, jobject obj):
        wr = WeakRef()
        if obj:
            wr.obj = env[0].NewWeakGlobalRef(env, obj)
        return wr

    def __dealloc__(self):
        cdef JNIEnv *j_env
        if self.obj:
            j_env = get_jnienv()
            j_env[0].DeleteWeakGlobalRef(j_env, self.obj)
        # The __dealloc__() method of the superclass will be called automatically.

    cdef WeakRef weak_ref(self):
        return self
