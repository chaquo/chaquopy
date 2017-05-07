# Classes and functions used by the Java module

from .jni cimport *

# === class ===================================================================

cdef class JavaObject(object):
    cdef GlobalRef j_self
    cdef void instantiate_from(self, GlobalRef j_self) except *

# === conversion ==============================================================

cdef convert_jobject_to_python(JNIEnv *j_env, definition, jobject j_object)
cdef jobject convert_python_to_jobject(JNIEnv *j_env, definition, obj) except *

# === env =====================================================================

cdef class GlobalRef(object):
    cdef jobject obj
    @staticmethod
    cdef GlobalRef create(JNIEnv *env, jobject obj)

# === jni =====================================================================

cdef void set_jvm(JavaVM *new_jvm)

# === utils ===================================================================

cdef void expect_exception(JNIEnv *j_env, msg) except *
cdef void check_exception(JNIEnv *j_env) except *
