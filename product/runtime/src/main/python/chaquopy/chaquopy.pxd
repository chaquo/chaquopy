# Classes and functions used by the Java module

from .jni cimport *

# === class ===================================================================

cdef class JavaObject(object):
    cdef GlobalRef j_self

# === conversion ==============================================================

cdef convert_jobject_to_python(JNIEnv *j_env, definition, jobject j_object)
cdef j2p_string(JNIEnv *env, jobject j_object)
cdef j2p_pyobject(JNIEnv *env, jobject jpyobject)
cdef convert_jarray_to_python(JNIEnv *j_env, definition, jobject j_object)

cdef JNIRef convert_python_to_jobject(JNIEnv *j_env, definition, obj)
cdef JNIRef p2j_string(JNIEnv *env, s)
cdef jobject p2j_pyobject(JNIEnv *env, obj) except *
cdef jobject convert_pyarray_to_java(JNIEnv *j_env, definition, pyarray) except *

# === env =====================================================================

cdef class JNIRef(object):
    cdef jobject obj

    cdef jobject release(self)
    cdef GlobalRef global_ref(self)

cdef class GlobalRef(JNIRef):
    @staticmethod
    cdef GlobalRef create(JNIEnv *env, jobject obj)

cdef class LocalRef(JNIRef):
    # It's safe to store j_env here, as long as the LocalRef isn't kept beyond the thread
    # detach or Java "native" method return.
    cdef JNIEnv *env

    @staticmethod
    cdef LocalRef create(JNIEnv *env, jobject obj)
    @staticmethod
    cdef LocalRef wrap(JNIEnv *env, jobject obj)

# === jni =====================================================================

cdef void set_jvm(JavaVM *new_jvm)

# === utils ===================================================================

cdef void expect_exception(JNIEnv *j_env, msg) except *
cdef void check_exception(JNIEnv *j_env) except *
