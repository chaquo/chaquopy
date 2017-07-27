from libc.stdint cimport uint8_t, int8_t, uint16_t, int16_t, int32_t, int64_t

# In Cython 0.25.2, "nogil" specified on the "cdef extern from" line had no effect on
# the individual functions, so we need to mark them individually.
#
# nogil in a .pyd only *allows* functions to be called without the GIL. It does not
# release the GIL in itself: for that, use "with nogil".
cdef extern from "jni.h":
    ctypedef uint8_t         jboolean
    ctypedef int8_t          jbyte
    ctypedef uint16_t        jchar
    ctypedef int16_t         jshort
    ctypedef int32_t         jint
    ctypedef int64_t         jlong
    ctypedef float           jfloat
    ctypedef double          jdouble
    ctypedef void*           jobject

    # These typedefs are for documentation only and are not enforced by the compiler.
    # Removed `jarray` and `jclass` typedefs because we have functions of the same names.
    ctypedef jobject         jstring
    ctypedef jobject         jthrowable
    ctypedef jobject         jweak
    ctypedef jint            jsize

    # Defining these using their true types of jint and jboolean caused Cython to generate an
    # assignment to JNI_VERSION_1_6 when compiling chaquopy_java.pyx. This gave exactly the
    # same type of error as at https://groups.google.com/forum/#!topic/cython-users/oPHbR3KmX2c,
    # but the explanation at https://github.com/mehcode/python-xmlsec/commit/01f8d0d4a275da190ca668fbc3a7a6fbeff01a18#commitcomment-13005096
    # does not seem to be relevant here.
    enum: JNI_VERSION_1_6
    enum: JNI_FALSE, JNI_TRUE
    enum: JNI_OK, JNI_ERR, JNI_EDETACHED, JNI_EVERSION, JNI_ENOMEM, JNI_EEXIST, JNI_EINVAL
    enum: JNI_COMMIT, JNI_ABORT

    ctypedef struct JNINativeMethod:
        const char* name
        const char* signature
        void*       fnPtr

    ctypedef union jvalue:
        jboolean    z
        jbyte       b
        jchar       c
        jshort      s
        jint        i
        jlong       j
        jfloat      f
        jdouble     d
        jobject     l

    ctypedef enum jobjectRefType:
        JNIInvalidRefType = 0,
        JNILocalRefType = 1,
        JNIGlobalRefType = 2,
        JNIWeakGlobalRefType = 3

    ctypedef void *jmethodID
    ctypedef void *jfieldID

    ctypedef struct JNINativeInterface
    ctypedef struct JNIInvokeInterface

    ctypedef JNINativeInterface* JNIEnv
    ctypedef JNIInvokeInterface* JavaVM

    ctypedef struct JNINativeInterface:
        jint *GetVersion(JNIEnv *)
        jobject     (*DefineClass)(JNIEnv*, const char*, jobject, const jbyte*, jsize)
        jobject     (*FindClass)(JNIEnv*, char*)

        jmethodID   (*FromReflectedMethod)(JNIEnv*, jobject)
        jfieldID    (*FromReflectedField)(JNIEnv*, jobject)
        # spec doesn't show jboolean parameter
        jobject     (*ToReflectedMethod)(JNIEnv*, jobject, jmethodID, jboolean)

        jobject     (*GetSuperclass)(JNIEnv*, jobject)
        jboolean    (*IsAssignableFrom)(JNIEnv*, jobject, jobject)

        # spec doesn't show jboolean parameter
        jobject     (*ToReflectedField)(JNIEnv*, jobject, jfieldID, jboolean)

        jint        (*Throw)(JNIEnv*, jthrowable)
        jint        (*ThrowNew)(JNIEnv *, jobject, const char *)
        jthrowable  (*ExceptionOccurred)(JNIEnv*)
        void        (*ExceptionDescribe)(JNIEnv*)
        void        (*ExceptionClear)(JNIEnv*)
        void        (*FatalError)(JNIEnv*, const char*)

        jint        (*PushLocalFrame)(JNIEnv*, jint)
        jobject     (*PopLocalFrame)(JNIEnv*, jobject)

        jobject     (*NewGlobalRef)(JNIEnv*, jobject)
        void        (*DeleteGlobalRef)(JNIEnv*, jobject)
        void        (*DeleteLocalRef)(JNIEnv*, jobject)
        jboolean    (*IsSameObject)(JNIEnv*, jobject, jobject)

        jobject     (*NewLocalRef)(JNIEnv*, jobject)
        jint        (*EnsureLocalCapacity)(JNIEnv*, jint)

        jobject     (*AllocObject)(JNIEnv*, jobject)

        # See note above about "nogil"
        jobject     (*NewObject)(JNIEnv*, jobject, jmethodID, ...) nogil
        jobject     (*NewObjectV)(JNIEnv*, jobject, jmethodID, va_list) nogil
        jobject     (*NewObjectA)(JNIEnv*, jobject, jmethodID, jvalue*) nogil

        jobject     (*GetObjectClass)(JNIEnv*, jobject)
        jboolean    (*IsInstanceOf)(JNIEnv*, jobject, jobject)
        jmethodID   (*GetMethodID)(JNIEnv*, jobject, const char*, const char*)

        # See note above about "nogil"
        jobject  (*CallObjectMethod)(JNIEnv*, jobject, jmethodID, ...) nogil
        jobject  (*CallObjectMethodV)(JNIEnv*, jobject, jmethodID, va_list) nogil
        jobject  (*CallObjectMethodA)(JNIEnv*, jobject, jmethodID, jvalue*) nogil
        jboolean (*CallBooleanMethod)(JNIEnv*, jobject, jmethodID, ...) nogil
        jboolean (*CallBooleanMethodV)(JNIEnv*, jobject, jmethodID, va_list) nogil
        jboolean (*CallBooleanMethodA)(JNIEnv*, jobject, jmethodID, jvalue*) nogil
        jbyte    (*CallByteMethod)(JNIEnv*, jobject, jmethodID, ...) nogil
        jbyte    (*CallByteMethodV)(JNIEnv*, jobject, jmethodID, va_list) nogil
        jbyte    (*CallByteMethodA)(JNIEnv*, jobject, jmethodID, jvalue*) nogil
        jchar    (*CallCharMethod)(JNIEnv*, jobject, jmethodID, ...) nogil
        jchar    (*CallCharMethodV)(JNIEnv*, jobject, jmethodID, va_list) nogil
        jchar    (*CallCharMethodA)(JNIEnv*, jobject, jmethodID, jvalue*) nogil
        jshort   (*CallShortMethod)(JNIEnv*, jobject, jmethodID, ...) nogil
        jshort   (*CallShortMethodV)(JNIEnv*, jobject, jmethodID, va_list) nogil
        jshort   (*CallShortMethodA)(JNIEnv*, jobject, jmethodID, jvalue*) nogil
        jint     (*CallIntMethod)(JNIEnv*, jobject, jmethodID, ...) nogil
        jint     (*CallIntMethodV)(JNIEnv*, jobject, jmethodID, va_list) nogil
        jint     (*CallIntMethodA)(JNIEnv*, jobject, jmethodID, jvalue*) nogil
        jlong    (*CallLongMethod)(JNIEnv*, jobject, jmethodID, ...) nogil
        jlong    (*CallLongMethodV)(JNIEnv*, jobject, jmethodID, va_list) nogil
        jlong    (*CallLongMethodA)(JNIEnv*, jobject, jmethodID, jvalue*) nogil
        jfloat   (*CallFloatMethod)(JNIEnv*, jobject, jmethodID, ...) nogil
        jfloat   (*CallFloatMethodV)(JNIEnv*, jobject, jmethodID, va_list) nogil
        jfloat   (*CallFloatMethodA)(JNIEnv*, jobject, jmethodID, jvalue*) nogil
        jdouble  (*CallDoubleMethod)(JNIEnv*, jobject, jmethodID, ...) nogil
        jdouble  (*CallDoubleMethodV)(JNIEnv*, jobject, jmethodID, va_list) nogil
        jdouble  (*CallDoubleMethodA)(JNIEnv*, jobject, jmethodID, jvalue*) nogil
        void     (*CallVoidMethod)(JNIEnv*, jobject, jmethodID, ...) nogil
        void     (*CallVoidMethodV)(JNIEnv*, jobject, jmethodID, va_list) nogil
        void     (*CallVoidMethodA)(JNIEnv*, jobject, jmethodID, jvalue*) nogil

        # See note above about "nogil"
        jobject  (*CallNonvirtualObjectMethod)(JNIEnv*, jobject, jobject, jmethodID, ...) nogil
        jobject  (*CallNonvirtualObjectMethodV)(JNIEnv*, jobject, jobject, jmethodID, va_list) nogil
        jobject  (*CallNonvirtualObjectMethodA)(JNIEnv*, jobject, jobject, jmethodID, jvalue*) nogil
        jboolean (*CallNonvirtualBooleanMethod)(JNIEnv*, jobject, jobject, jmethodID, ...) nogil
        jboolean (*CallNonvirtualBooleanMethodV)(JNIEnv*, jobject, jobject, jmethodID, va_list) nogil
        jboolean (*CallNonvirtualBooleanMethodA)(JNIEnv*, jobject, jobject, jmethodID, jvalue*) nogil
        jbyte    (*CallNonvirtualByteMethod)(JNIEnv*, jobject, jobject, jmethodID, ...) nogil
        jbyte    (*CallNonvirtualByteMethodV)(JNIEnv*, jobject, jobject, jmethodID, va_list) nogil
        jbyte    (*CallNonvirtualByteMethodA)(JNIEnv*, jobject, jobject, jmethodID, jvalue*) nogil
        jchar    (*CallNonvirtualCharMethod)(JNIEnv*, jobject, jobject, jmethodID, ...) nogil
        jchar    (*CallNonvirtualCharMethodV)(JNIEnv*, jobject, jobject, jmethodID, va_list) nogil
        jchar    (*CallNonvirtualCharMethodA)(JNIEnv*, jobject, jobject, jmethodID, jvalue*) nogil
        jshort   (*CallNonvirtualShortMethod)(JNIEnv*, jobject, jobject, jmethodID, ...) nogil
        jshort   (*CallNonvirtualShortMethodV)(JNIEnv*, jobject, jobject, jmethodID, va_list) nogil
        jshort   (*CallNonvirtualShortMethodA)(JNIEnv*, jobject, jobject, jmethodID, jvalue*) nogil
        jint     (*CallNonvirtualIntMethod)(JNIEnv*, jobject, jobject, jmethodID, ...) nogil
        jint     (*CallNonvirtualIntMethodV)(JNIEnv*, jobject, jobject, jmethodID, va_list) nogil
        jint     (*CallNonvirtualIntMethodA)(JNIEnv*, jobject, jobject, jmethodID, jvalue*) nogil
        jlong    (*CallNonvirtualLongMethod)(JNIEnv*, jobject, jobject, jmethodID, ...) nogil
        jlong    (*CallNonvirtualLongMethodV)(JNIEnv*, jobject, jobject, jmethodID, va_list) nogil
        jlong    (*CallNonvirtualLongMethodA)(JNIEnv*, jobject, jobject, jmethodID, jvalue*) nogil
        jfloat   (*CallNonvirtualFloatMethod)(JNIEnv*, jobject, jobject, jmethodID, ...) nogil
        jfloat   (*CallNonvirtualFloatMethodV)(JNIEnv*, jobject, jobject, jmethodID, va_list) nogil
        jfloat   (*CallNonvirtualFloatMethodA)(JNIEnv*, jobject, jobject, jmethodID, jvalue*) nogil
        jdouble  (*CallNonvirtualDoubleMethod)(JNIEnv*, jobject, jobject, jmethodID, ...) nogil
        jdouble  (*CallNonvirtualDoubleMethodV)(JNIEnv*, jobject, jobject, jmethodID, va_list) nogil
        jdouble  (*CallNonvirtualDoubleMethodA)(JNIEnv*, jobject, jobject, jmethodID, jvalue*) nogil
        void     (*CallNonvirtualVoidMethod)(JNIEnv*, jobject, jobject, jmethodID, ...) nogil
        void     (*CallNonvirtualVoidMethodV)(JNIEnv*, jobject, jobject, jmethodID, va_list) nogil
        void     (*CallNonvirtualVoidMethodA)(JNIEnv*, jobject, jobject, jmethodID, jvalue*) nogil

        jfieldID    (*GetFieldID)(JNIEnv*, jobject, const char*, const char*)

        jobject     (*GetObjectField)(JNIEnv*, jobject, jfieldID)
        jboolean    (*GetBooleanField)(JNIEnv*, jobject, jfieldID)
        jbyte       (*GetByteField)(JNIEnv*, jobject, jfieldID)
        jchar       (*GetCharField)(JNIEnv*, jobject, jfieldID)
        jshort      (*GetShortField)(JNIEnv*, jobject, jfieldID)
        jint        (*GetIntField)(JNIEnv*, jobject, jfieldID)
        jlong       (*GetLongField)(JNIEnv*, jobject, jfieldID)
        jfloat      (*GetFloatField)(JNIEnv*, jobject, jfieldID)
        jdouble     (*GetDoubleField)(JNIEnv*, jobject, jfieldID)

        void        (*SetObjectField)(JNIEnv*, jobject, jfieldID, jobject)
        void        (*SetBooleanField)(JNIEnv*, jobject, jfieldID, jboolean)
        void        (*SetByteField)(JNIEnv*, jobject, jfieldID, jbyte)
        void        (*SetCharField)(JNIEnv*, jobject, jfieldID, jchar)
        void        (*SetShortField)(JNIEnv*, jobject, jfieldID, jshort)
        void        (*SetIntField)(JNIEnv*, jobject, jfieldID, jint)
        void        (*SetLongField)(JNIEnv*, jobject, jfieldID, jlong)
        void        (*SetFloatField)(JNIEnv*, jobject, jfieldID, jfloat)
        void        (*SetDoubleField)(JNIEnv*, jobject, jfieldID, jdouble)

        jmethodID   (*GetStaticMethodID)(JNIEnv*, jobject, const char*, const char*)

        # See note above about "nogil"
        jobject  (*CallStaticObjectMethod)(JNIEnv*, jobject, jmethodID, ...) nogil
        jobject  (*CallStaticObjectMethodV)(JNIEnv*, jobject, jmethodID, va_list) nogil
        jobject  (*CallStaticObjectMethodA)(JNIEnv*, jobject, jmethodID, jvalue*) nogil
        jboolean (*CallStaticBooleanMethod)(JNIEnv*, jobject, jmethodID, ...) nogil
        jboolean (*CallStaticBooleanMethodV)(JNIEnv*, jobject, jmethodID, va_list) nogil
        jboolean (*CallStaticBooleanMethodA)(JNIEnv*, jobject, jmethodID, jvalue*) nogil
        jbyte    (*CallStaticByteMethod)(JNIEnv*, jobject, jmethodID, ...) nogil
        jbyte    (*CallStaticByteMethodV)(JNIEnv*, jobject, jmethodID, va_list) nogil
        jbyte    (*CallStaticByteMethodA)(JNIEnv*, jobject, jmethodID, jvalue*) nogil
        jchar    (*CallStaticCharMethod)(JNIEnv*, jobject, jmethodID, ...) nogil
        jchar    (*CallStaticCharMethodV)(JNIEnv*, jobject, jmethodID, va_list) nogil
        jchar    (*CallStaticCharMethodA)(JNIEnv*, jobject, jmethodID, jvalue*) nogil
        jshort   (*CallStaticShortMethod)(JNIEnv*, jobject, jmethodID, ...) nogil
        jshort   (*CallStaticShortMethodV)(JNIEnv*, jobject, jmethodID, va_list) nogil
        jshort   (*CallStaticShortMethodA)(JNIEnv*, jobject, jmethodID, jvalue*) nogil
        jint     (*CallStaticIntMethod)(JNIEnv*, jobject, jmethodID, ...) nogil
        jint     (*CallStaticIntMethodV)(JNIEnv*, jobject, jmethodID, va_list) nogil
        jint     (*CallStaticIntMethodA)(JNIEnv*, jobject, jmethodID, jvalue*) nogil
        jlong    (*CallStaticLongMethod)(JNIEnv*, jobject, jmethodID, ...) nogil
        jlong    (*CallStaticLongMethodV)(JNIEnv*, jobject, jmethodID, va_list) nogil
        jlong    (*CallStaticLongMethodA)(JNIEnv*, jobject, jmethodID, jvalue*) nogil
        jfloat   (*CallStaticFloatMethod)(JNIEnv*, jobject, jmethodID, ...) nogil
        jfloat   (*CallStaticFloatMethodV)(JNIEnv*, jobject, jmethodID, va_list) nogil
        jfloat   (*CallStaticFloatMethodA)(JNIEnv*, jobject, jmethodID, jvalue*) nogil
        jdouble  (*CallStaticDoubleMethod)(JNIEnv*, jobject, jmethodID, ...) nogil
        jdouble  (*CallStaticDoubleMethodV)(JNIEnv*, jobject, jmethodID, va_list) nogil
        jdouble  (*CallStaticDoubleMethodA)(JNIEnv*, jobject, jmethodID, jvalue*) nogil
        void     (*CallStaticVoidMethod)(JNIEnv*, jobject, jmethodID, ...) nogil
        void     (*CallStaticVoidMethodV)(JNIEnv*, jobject, jmethodID, va_list) nogil
        void     (*CallStaticVoidMethodA)(JNIEnv*, jobject, jmethodID, jvalue*) nogil

        jfieldID    (*GetStaticFieldID)(JNIEnv*, jobject, const char*, const char*)

        jobject     (*GetStaticObjectField)(JNIEnv*, jobject, jfieldID)
        jboolean    (*GetStaticBooleanField)(JNIEnv*, jobject, jfieldID)
        jbyte       (*GetStaticByteField)(JNIEnv*, jobject, jfieldID)
        jchar       (*GetStaticCharField)(JNIEnv*, jobject, jfieldID)
        jshort      (*GetStaticShortField)(JNIEnv*, jobject, jfieldID)
        jint        (*GetStaticIntField)(JNIEnv*, jobject, jfieldID)
        jlong       (*GetStaticLongField)(JNIEnv*, jobject, jfieldID)
        jfloat      (*GetStaticFloatField)(JNIEnv*, jobject, jfieldID)
        jdouble     (*GetStaticDoubleField)(JNIEnv*, jobject, jfieldID)

        void        (*SetStaticObjectField)(JNIEnv*, jobject, jfieldID, jobject)
        void        (*SetStaticBooleanField)(JNIEnv*, jobject, jfieldID, jboolean)
        void        (*SetStaticByteField)(JNIEnv*, jobject, jfieldID, jbyte)
        void        (*SetStaticCharField)(JNIEnv*, jobject, jfieldID, jchar)
        void        (*SetStaticShortField)(JNIEnv*, jobject, jfieldID, jshort)
        void        (*SetStaticIntField)(JNIEnv*, jobject, jfieldID, jint)
        void        (*SetStaticLongField)(JNIEnv*, jobject, jfieldID, jlong)
        void        (*SetStaticFloatField)(JNIEnv*, jobject, jfieldID, jfloat)
        void        (*SetStaticDoubleField)(JNIEnv*, jobject, jfieldID, jdouble)

        jstring     (*NewString)(JNIEnv*, const jchar*, jsize)
        jsize       (*GetStringLength)(JNIEnv*, jstring)
        const jchar* (*GetStringChars)(JNIEnv*, jstring, jboolean*)
        void        (*ReleaseStringChars)(JNIEnv*, jstring, const jchar*)
        jstring     (*NewStringUTF)(JNIEnv*, char*)
        jsize       (*GetStringUTFLength)(JNIEnv*, jstring)
        # JNI spec says this returns const jbyte*, but that's inconsistent
        const char* (*GetStringUTFChars)(JNIEnv*, jstring, jboolean*)
        void        (*ReleaseStringUTFChars)(JNIEnv*, jstring, const char*)
        jsize       (*GetArrayLength)(JNIEnv*, jobject)
        jobject     (*NewObjectArray)(JNIEnv*, jsize, jobject, jobject)
        jobject     (*GetObjectArrayElement)(JNIEnv*, jobject, jsize)
        void        (*SetObjectArrayElement)(JNIEnv*, jobject, jsize, jobject)

        jobject     (*NewBooleanArray)(JNIEnv*, jsize)
        jobject     (*NewByteArray)(JNIEnv*, jsize)
        jobject     (*NewCharArray)(JNIEnv*, jsize)
        jobject     (*NewShortArray)(JNIEnv*, jsize)
        jobject     (*NewIntArray)(JNIEnv*, jsize)
        jobject     (*NewLongArray)(JNIEnv*, jsize)
        jobject     (*NewFloatArray)(JNIEnv*, jsize)
        jobject     (*NewDoubleArray)(JNIEnv*, jsize)

        jboolean*   (*GetBooleanArrayElements)(JNIEnv*, jobject, jboolean*)
        jbyte*      (*GetByteArrayElements)(JNIEnv*, jobject, jboolean*)
        jchar*      (*GetCharArrayElements)(JNIEnv*, jobject, jboolean*)
        jshort*     (*GetShortArrayElements)(JNIEnv*, jobject, jboolean*)
        jint*       (*GetIntArrayElements)(JNIEnv*, jobject, jboolean*)
        jlong*      (*GetLongArrayElements)(JNIEnv*, jobject, jboolean*)
        jfloat*     (*GetFloatArrayElements)(JNIEnv*, jobject, jboolean*)
        jdouble*    (*GetDoubleArrayElements)(JNIEnv*, jobject, jboolean*)

        void        (*ReleaseBooleanArrayElements)(JNIEnv*, jobject, jboolean*, jint)
        void        (*ReleaseByteArrayElements)(JNIEnv*, jobject, jbyte*, jint)
        void        (*ReleaseCharArrayElements)(JNIEnv*, jobject, jchar*, jint)
        void        (*ReleaseShortArrayElements)(JNIEnv*, jobject, jshort*, jint)
        void        (*ReleaseIntArrayElements)(JNIEnv*, jobject, jint*, jint)
        void        (*ReleaseLongArrayElements)(JNIEnv*, jobject, jlong*, jint)
        void        (*ReleaseFloatArrayElements)(JNIEnv*, jobject, jfloat*, jint)
        void        (*ReleaseDoubleArrayElements)(JNIEnv*, jobject, jdouble*, jint)

        void        (*GetBooleanArrayRegion)(JNIEnv*, jobject, jsize, jsize, jboolean*)
        void        (*GetByteArrayRegion)(JNIEnv*, jobject, jsize, jsize, jbyte*)
        void        (*GetCharArrayRegion)(JNIEnv*, jobject, jsize, jsize, jchar*)
        void        (*GetShortArrayRegion)(JNIEnv*, jobject, jsize, jsize, jshort*)
        void        (*GetIntArrayRegion)(JNIEnv*, jobject, jsize, jsize, jint*)
        void        (*GetLongArrayRegion)(JNIEnv*, jobject, jsize, jsize, jlong*)
        void        (*GetFloatArrayRegion)(JNIEnv*, jobject, jsize, jsize, jfloat*)
        void        (*GetDoubleArrayRegion)(JNIEnv*, jobject, jsize, jsize, jdouble*)

        # spec shows these without const some jni.h do, some don't
        void        (*SetBooleanArrayRegion)(JNIEnv*, jobject, jsize, jsize, const jboolean*)
        void        (*SetByteArrayRegion)(JNIEnv*, jobject, jsize, jsize, const jbyte*)
        void        (*SetCharArrayRegion)(JNIEnv*, jobject, jsize, jsize, const jchar*)
        void        (*SetShortArrayRegion)(JNIEnv*, jobject, jsize, jsize, const jshort*)
        void        (*SetIntArrayRegion)(JNIEnv*, jobject, jsize, jsize, const jint*)
        void        (*SetLongArrayRegion)(JNIEnv*, jobject, jsize, jsize, const jlong*)
        void        (*SetFloatArrayRegion)(JNIEnv*, jobject, jsize, jsize, const jfloat*)
        void        (*SetDoubleArrayRegion)(JNIEnv*, jobject, jsize, jsize, const jdouble*)

        jint        (*RegisterNatives)(JNIEnv*, jobject, const JNINativeMethod*, jint)
        jint        (*UnregisterNatives)(JNIEnv*, jobject)
        jint        (*MonitorEnter)(JNIEnv*, jobject) nogil  # See note above about "nogil"
        jint        (*MonitorExit)(JNIEnv*, jobject)
        jint        (*GetJavaVM)(JNIEnv*, JavaVM**)

        void        (*GetStringRegion)(JNIEnv*, jstring, jsize, jsize, jchar*)
        void        (*GetStringUTFRegion)(JNIEnv*, jstring, jsize, jsize, char*)

        void*       (*GetPrimitiveArrayCritical)(JNIEnv*, jobject, jboolean*)
        void        (*ReleasePrimitiveArrayCritical)(JNIEnv*, jobject, void*, jint)

        const jchar* (*GetStringCritical)(JNIEnv*, jstring, jboolean*)
        void        (*ReleaseStringCritical)(JNIEnv*, jstring, const jchar*)

        jweak       (*NewWeakGlobalRef)(JNIEnv*, jobject)
        void        (*DeleteWeakGlobalRef)(JNIEnv*, jweak)

        jboolean    (*ExceptionCheck)(JNIEnv*)

        jobject     (*NewDirectByteBuffer)(JNIEnv*, void*, jlong)
        void*       (*GetDirectBufferAddress)(JNIEnv*, jobject)
        jlong       (*GetDirectBufferCapacity)(JNIEnv*, jobject)

        jobjectRefType (*GetObjectRefType)(JNIEnv*, jobject)

    # p_env should be a JNIEnv ** (and is defined that way in the Android NDK headers), but
    # it's defined as a void ** in the JNI spec and the Oracle headers. We work around this
    # in chaquopy_extra.h.
    ctypedef JNIEnv Attach_JNIEnv

    ctypedef struct JNIInvokeInterface:
        jint        (*AttachCurrentThread)(JavaVM *vm, Attach_JNIEnv **p_env, void *thr_args)
        jint        (*DetachCurrentThread)(JavaVM *vm)

    ctypedef struct JavaVMInitArgs:
        jint version
        jint nOptions
        jboolean ignoreUnrecognized
        JavaVMOption *options

    ctypedef struct JavaVMOption:
        char *optionString
        void *extraInfo
