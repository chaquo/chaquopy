# Classes and functions used by the Java module

from .jni cimport *

# === conversion ==============================================================

cdef j2p(JNIEnv *j_env, JNIRef j_object)
cdef j2p_string(JNIEnv *env, jobject j_object)
cdef j2p_pyobject(JNIEnv *env, jobject jpyobject)

cdef p2j(JNIEnv *j_env, definition, obj, bint autobox=?)
cdef JNIRef p2j_string(JNIEnv *env, s)
cdef jobject p2j_pyobject(JNIEnv *env, obj) except *

# === env =====================================================================

cdef class JNIRef(object):
    cdef jobject obj
    cdef GlobalRef global_ref(self)
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

# === jvm =====================================================================

cdef set_jvm(JavaVM *new_jvm)
