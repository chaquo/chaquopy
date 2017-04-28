# Functions called from the Java module

from .jni cimport *

# jni
cdef void set_jvm(JavaVM *new_jvm)

# conversion
cdef convert_jobject_to_python(JNIEnv *j_env, definition, jobject j_object)
cdef jobject convert_python_to_jobject(JNIEnv *j_env, definition, obj) except *
