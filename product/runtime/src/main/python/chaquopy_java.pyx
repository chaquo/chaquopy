from __future__ import print_function, unicode_literals

from cpython.module cimport PyImport_ImportModule
from libc.errno cimport errno
from libc.stdio cimport printf, snprintf
from libc.stdlib cimport malloc
from libc.string cimport strerror, strlen
from posix.stdlib cimport putenv

from chaquopy.jni cimport *
from chaquopy.chaquopy cimport *

cdef extern from "Python.h":
    void Py_Initialize()

cdef extern from "chaquopy_java_init.h":
    void initchaquopy_java() except *  # TODO #5148 (name changes in Python 3)
    const char *__Pyx_BUILTIN_MODULE_NAME

cdef public jint JNI_OnLoad(JavaVM *jvm, void *reserved):
    return JNI_VERSION_1_6


cdef public void Java_com_chaquo_python_Python_start \
    (JNIEnv *env, jclass klass, jstring jPythonPath):
    # All code run before Py_Initialize must compile to pure C.
    if jPythonPath != NULL:
        if not set_path(env, jPythonPath):
            return
    Py_Initialize()  # Calls abort() on failure

    # We can now start using some Python constructs, but many things will still cause a crash
    # until our module initialization function completes. In particular, global and built-in
    # names won't be bound.
    try:
        initchaquopy_java()
    except Exception as e:
        java_exception(env, traceback_format_exc(e))
        return
    # OK, normal Cython functionality is now available.

    # Prevent the Python module from trying to start Java
    cdef JavaVM *jvm = NULL
    if env[0].GetJavaVM(env, &jvm) != 0:
         java_exception(env, "GetJavaVM failed")
         return
    set_jvm(jvm)


cdef bint set_path(JNIEnv *env, jstring jPythonPath):
    cdef const char *pythonPath = env[0].GetStringUTFChars(env, jPythonPath, NULL)
    if pythonPath == NULL:
        java_exception(env, "GetStringUTFChars failed")
        return False

    # setenv is easier to use, but is not available on MSYS2.
    cdef const char *putenvPrefix = "PYTHONPATH="
    cdef int putenvArgLen = strlen(putenvPrefix) + strlen(pythonPath) + 1
    cdef char *putenvArg = <char*>malloc(putenvArgLen)
    if snprintf(putenvArg, putenvArgLen, "%s%s", putenvPrefix, pythonPath) != (putenvArgLen - 1):
        java_exception(env, "snprintf failed")
        return False
    env[0].ReleaseStringUTFChars(env, jPythonPath, pythonPath)

    # putenv takes ownership of the string passed to it.
    if putenv(putenvArg) != 0:
        java_exception(env, "putenv failed")
        return False
    return True


cdef traceback_format_exc(Exception e):
    # Cython translates "import" into code which references the chaquopy_java module object,
    # which doesn't exist if the module initialization function failed. So we'll have to do it
    # manually.
    try:
        traceback = PyImport_ImportModule("traceback")
        result = traceback.format_exc()
    except Exception as e2:
        result = (f"{type(e).__name__}: {e} "
                  f"[Failed to get traceback: {type(e2).__name__}: {e2}]")
    return result.encode("UTF-8")


cdef void java_exception(JNIEnv *env, char *message):
    cdef jclass re = env[0].FindClass(env, "com/chaquo/python/PyException")
    if re != NULL:
        if env[0].ThrowNew(env, re, message) == 0:
            return
    printf("Failed to throw Java exception: %s", message)


cdef public jstring Java_com_chaquo_python_Python_getModule \
    (JNIEnv *env, jobject this, jstring name) with gil:
    return NULL  # FIXME


cdef public jstring Java_com_chaquo_python_Python_hello \
    (JNIEnv *env, jobject this, jstring s) with gil:
    result = "hello " + convert_jobject_to_python(env, "Ljava/lang/String;", s)
    return convert_python_to_jobject(env, "Ljava/lang/String;", result)


cdef public jint Java_com_chaquo_python_Python_add \
    (JNIEnv *env, jobject this, jint x) with gil:
    return x + 42
