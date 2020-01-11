# cython: language_level=2

from .jni cimport *

# === conversion ==============================================================

cdef j2p(JNIEnv *j_env, JNIRef j_object)
cdef j2p_string(JNIEnv *env, JNIRef j_string)
cdef j2p_pyobject(JNIEnv *env, jobject jpyobject)

cdef p2j(JNIEnv *j_env, definition, obj, bint autobox=?)
cdef JNIRef p2j_string(JNIEnv *env, s)
cdef jobject p2j_pyobject(JNIEnv *env, obj) except? NULL

cdef box_sig(JNIEnv *j_env, JNIRef j_klass)

# === env =====================================================================

cdef class JNIRef(object):
    cdef jobject obj
    cdef jint hash_code
    cdef GlobalRef global_ref(self)
    cdef WeakRef weak_ref(self)
    cdef jobject return_ref(self, JNIEnv *env)

cdef class GlobalRef(JNIRef):
    @staticmethod
    cdef GlobalRef create(JNIEnv *env, jobject obj)
    cdef GlobalRef global_ref(self)

cdef class LocalRef(JNIRef):
    # It's safe to store j_env here, as long as the LocalRef isn't kept beyond the thread
    # detach or Java "native" method return.
    cdef JNIEnv *env

    @staticmethod
    cdef LocalRef create(JNIEnv *env, jobject obj)
    @staticmethod
    cdef LocalRef adopt(JNIEnv *env, jobject obj)
    cdef GlobalRef global_ref(self)

cdef class WeakRef(JNIRef):
    @staticmethod
    cdef WeakRef create(JNIEnv *env, jobject obj)
    cdef WeakRef weak_ref(self)

# === jvm =====================================================================

cdef JNIEnv *get_jnienv() except NULL
cdef set_jvm(JavaVM *new_jvm)

# === license =================================================================

cdef check_license(platform)
