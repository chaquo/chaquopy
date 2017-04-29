# Classes and functions used by the Java module

from .jni cimport *


# === class ===================================================================

cdef class JavaClass(object):
    cdef GlobalRef j_self
    cdef void instantiate_from(self, GlobalRef j_self) except *
    cdef void call_constructor(self, args) except *

cdef class JavaMember(object):
    cdef jc
    cdef name
    cdef bint is_static

cdef class JavaField(JavaMember):
    cdef jfieldID j_field
    cdef definition
    cdef void ensure_field(self) except *
    cdef write_field(self, jobject j_self, value)
    cdef read_field(self, jobject j_self)
    cdef read_static_field(self)

cdef class JavaMethod(JavaMember):
    cdef jmethodID j_method
    cdef definition
    cdef object definition_return
    cdef object definition_args
    cdef bint is_varargs
    cdef void ensure_method(self) except *
    cdef call_method(self, JNIEnv *j_env, JavaClass obj, jvalue *j_args)
    cdef call_staticmethod(self, JNIEnv *j_env, jvalue *j_args)

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
