from __future__ import absolute_import, division, print_function

from importlib import import_module

from cpython.module cimport PyImport_ImportModule
from cpython.object cimport PyObject
from cpython.ref cimport Py_INCREF, Py_DECREF
cdef extern from "Python.h":
    void Py_Initialize()
from libc.errno cimport errno
from libc.stdio cimport printf, snprintf
from libc.stdint cimport uintptr_t
from libc.stdlib cimport malloc
from libc.string cimport strerror, strlen
from posix.stdlib cimport putenv

from chaquopy.reflect import *
from chaquopy.jni cimport *
from chaquopy.chaquopy cimport *
cdef extern from "chaquopy_java_init.h":
    void initchaquopy_java() except *  # TODO #5148 (name changes in Python 3)
    const char *__Pyx_BUILTIN_MODULE_NAME


cdef public jint JNI_OnLoad(JavaVM *jvm, void *reserved):
    return JNI_VERSION_1_6


# === com.chaquo.python.Python ================================================

cdef public void Java_com_chaquo_python_Python_start \
    (JNIEnv *env, jclass klass, jstring jPythonPath):
    # All code run before Py_Initialize must compile to pure C.
    cdef JavaVM *jvm = NULL

    if jPythonPath != NULL:
        if not set_path(env, jPythonPath):
            return
    Py_Initialize()  # Calls abort() on failure

    # We can now start using some Python constructs, but many things will still cause a native
    # crash until our module initialization function completes. In particular, global and
    # built-in names won't be bound.
    try:
        initchaquopy_java()

        # Normal Cython functionality is now available.
        if env[0].GetJavaVM(env, &jvm) != 0:
             raise Exception("GetJavaVM failed")
        set_jvm(jvm)

        global JPyObject
        JPyObject = autoclass("com.chaquo.python.PyObject")

    except Exception as e:
        wrap_exception(env, e)


# This runs before Py_Initialize, so it must compile to pure C.
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


cdef public jobject Java_com_chaquo_python_Python_getModule \
    (JNIEnv *env, jobject this, jstring name) with gil:
    try:
        return get_jpyobject(env, import_module(j2p_str(env, name)))
    except Exception as e:
        wrap_exception(env, e)
        return NULL

# === com.chaquo.python.PyObject ==============================================

cdef get_object(JNIEnv *env, jobject this):
    cdef PyObject *po = <PyObject*><jlong>JPyObject(instance=GlobalRef.create(env, this)).obj
    if po == NULL:
        raise ValueError("PyObject is closed")
    return <object>po


# FIXME test this actually destroys the underlying object
cdef public void Java_com_chaquo_python_PyObject_close \
    (JNIEnv *env, jobject this) with gil:
    try:
        Py_DECREF(get_object(env, this))
        JPyObject(instance=GlobalRef.create(env, this)).obj = 0
    except Exception as e:
        wrap_exception(env, e)


cdef public jstring Java_com_chaquo_python_PyObject_toString \
    (JNIEnv *env, jobject this) with gil:
    try:
        return p2j_str(env, str(get_object(env, this)))
    except Exception as e:
        wrap_exception(env, e)
        return NULL

# =============================================================================

cdef jobject get_jpyobject(JNIEnv *env, obj) except NULL:
    cdef JavaObject jpo = JPyObject.getInstance(<jlong><PyObject*>obj)
    Py_INCREF(obj)
    return env[0].NewLocalRef(env, jpo.j_self.obj)


# TODO if this is a Java exception, use the original exception object.
# TODO Integrate Python traceback into Java traceback if possible
#
# To do either of these things, create a new function called wrap_exception, rename this
# original function, and only call it from Python_start() when module initialization failed.
cdef wrap_exception(JNIEnv *env, Exception e):
    # Cython translates "import" into code which references the chaquopy_java module object,
    # which doesn't exist if the module initialization function failed with an exception. So
    # we'll have to do it manually.
    try:
        traceback = PyImport_ImportModule("traceback")
        result = traceback.format_exc()
    except Exception as e2:
        result = (f"{type(e).__name__}: {e} "
                  f"[Failed to get traceback: {type(e2).__name__}: {e2}]")
    java_exception(env, result.encode("UTF-8"))


# This may run before Py_Initialize, so it must compile to pure C.
cdef void java_exception(JNIEnv *env, char *message):
    cdef jclass re = env[0].FindClass(env, "com/chaquo/python/PyException")
    if re != NULL:
        if env[0].ThrowNew(env, re, message) == 0:
            return
    printf("Failed to throw Java exception: %s", message)


cdef jobject p2j_str(JNIEnv *env, s) except *:
    return convert_python_to_jobject(env, "Ljava/lang/String;", s)

cdef j2p_str(JNIEnv *env, jstring s):
    return convert_jobject_to_python(env, "Ljava/lang/String;", s)


# FIXME remove once real tests work
cdef public jstring Java_com_chaquo_python_Python_hello \
    (JNIEnv *env, jobject this, jstring s) with gil:
    try:
        return p2j_str(env, "hello " + j2p_str(env, s))
    except Exception as e:
        wrap_exception(env, e)
        return NULL


cdef public jint Java_com_chaquo_python_Python_add \
    (JNIEnv *env, jobject this, jint x) with gil:
    return x + 42
