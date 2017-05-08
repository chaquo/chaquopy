from __future__ import absolute_import, division, print_function

from importlib import import_module
import sys

from cpython.module cimport PyImport_ImportModule
from cpython.object cimport PyObject
from cpython.ref cimport Py_INCREF, Py_DECREF
cdef extern from "Python.h":
    void Py_Initialize()
    void PyEval_SaveThread()

from libc.errno cimport errno
from libc.stdio cimport printf, snprintf
from libc.stdint cimport uintptr_t
from libc.stdlib cimport malloc
from libc.string cimport strerror, strlen
from posix.stdlib cimport putenv

from chaquopy.reflect import *
from chaquopy.signatures import jni_sig
from chaquopy.jni cimport *
from chaquopy.chaquopy cimport *
cdef extern from "chaquopy_java_init.h":
    void initchaquopy_java() except *  # TODO #5148 (name changes in Python 3)


cdef public jint JNI_OnLoad(JavaVM *jvm, void *reserved):
    return JNI_VERSION_1_6


# === com.chaquo.python.Python ================================================

# This function will crash if called more than once!
cdef public void Java_com_chaquo_python_Python_startNative \
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
        ret = env[0].GetJavaVM(env, &jvm)
        if ret != 0:
             raise Exception(f"GetJavaVM failed: {ret}")
        set_jvm(jvm)

    except Exception as e:
        wrap_exception(env, e)

    # We imported chaquopy.chaquopy above, which has called PyEval_InitThreads during its own
    # module intialization, so the GIL now exists and we have it. We must release the GIL
    # before we return to Java so that the methods below can be called from any thread.
    # (http://bugs.python.org/issue1720250)
    PyEval_SaveThread();


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
        return p2j_pyobject(env, import_module(j2p_string(env, name)))
    except Exception as e:
        wrap_exception(env, e)
        return NULL


cdef public jobject Java_com_chaquo_python_Python_getBuiltins \
    (JNIEnv *env, jobject this) with gil:
    try:
        return p2j_pyobject(env, import_module("six.moves.builtins"))
    except Exception as e:
        wrap_exception(env, e)
        return NULL

# === com.chaquo.python.PyObject ==============================================

cdef public void Java_com_chaquo_python_PyObject_openNative \
    (JNIEnv *env, jobject this) with gil:
    try:
        Py_INCREF(j2p_pyobject(env, this))
    except Exception as e:
        wrap_exception(env, e)


cdef public void Java_com_chaquo_python_PyObject_closeNative \
    (JNIEnv *env, jobject this) with gil:
    try:
        Py_DECREF(j2p_pyobject(env, this))
    except Exception as e:
        wrap_exception(env, e)


cdef public jobject Java_com_chaquo_python_PyObject_fromJava \
    (JNIEnv *env, jobject klass, jobject o) with gil:
    try:
        return p2j_pyobject(env, j2p(env, "Ljava/lang/Object", o))
    except Exception as e:
        wrap_exception(env, e)
        return NULL


cdef public jobject Java_com_chaquo_python_PyObject_toJava \
    (JNIEnv *env, jobject this, jobject to_klass) with gil:
    try:
        Class = autoclass("java.lang.Class")
        to_sig = jni_sig(Class(instance=GlobalRef.create(env, to_klass)))
        result = p2j(env, to_sig, j2p_pyobject(env, this))
        return env[0].NewLocalRef(env, result.obj)
    except Exception as e:
        wrap_exception(env, e)
        return NULL


cdef public jlong Java_com_chaquo_python_PyObject_id \
    (JNIEnv *env, jobject this) with gil:
    try:
        return id(j2p_pyobject(env, this))
    except Exception as e:
        wrap_exception(env, e)
        return 0


cdef public jobject Java_com_chaquo_python_PyObject_type \
    (JNIEnv *env, jobject this) with gil:
    try:
        return p2j_pyobject(env, type(j2p_pyobject(env, this)))
    except Exception as e:
        wrap_exception(env, e)
        return NULL


cdef public jobject Java_com_chaquo_python_PyObject_call \
    (JNIEnv *env, jobject this, jarray jargs) with gil:
    try:
        if jargs == NULL:
            # User typed ".call(null)", which Java interprets as a null array, rather than the
            # array of one null which they intended.
            args = [None]
        else:
            args = j2p_array(env, "Ljava/lang/Object;", jargs)
        result = j2p_pyobject(env, this)(*args)
        return p2j_pyobject(env, result)
    except Exception as e:
        wrap_exception(env, e)
        return NULL


cdef public jboolean Java_com_chaquo_python_PyObject_containsKey \
    (JNIEnv *env, jobject this, jobject key) with gil:
    try:
        return hasattr(j2p_pyobject(env, this), j2p_string(env, key))
    except Exception as e:
        wrap_exception(env, e)
        return False


cdef public jobject Java_com_chaquo_python_PyObject_get \
    (JNIEnv *env, jobject this, jobject key) with gil:
    try:
        return p2j_pyobject(env, getattr(j2p_pyobject(env, this), j2p_string(env, key)))
    except Exception as e:
        wrap_exception(env, e)
        return NULL


cdef public jobject Java_com_chaquo_python_PyObject_put \
    (JNIEnv *env, jobject this, jobject key, jobject value) with gil:
    try:
        self = j2p_pyobject(env, this)
        str_key = j2p_string(env, key)
        try:
            old_value = getattr(self, str_key)
        except AttributeError:
            old_value = None
        setattr(self, str_key, j2p(env, "Ljava/lang/Object;", value))
        return p2j_pyobject(env, old_value)
    except Exception as e:
        wrap_exception(env, e)
        return NULL


cdef public jobject Java_com_chaquo_python_PyObject_remove \
    (JNIEnv *env, jobject this, jobject key) with gil:
    try:
        self = j2p_pyobject(env, this)
        str_key = j2p_string(env, key)
        try:
            old_value = getattr(self, str_key)
        except AttributeError:
            return NULL
        delattr(self, str_key)
        return p2j_pyobject(env, old_value)
    except Exception as e:
        wrap_exception(env, e)
        return NULL


cdef public jobject Java_com_chaquo_python_PyObject_dir \
    (JNIEnv *env, jobject this) with gil:
    cdef JavaObject keys
    try:
        keys = autoclass("java.util.ArrayList")()
        for key in dir(j2p_pyobject(env, this)):
            keys.add(key)
        return env[0].NewLocalRef(env, keys.j_self.obj)
    except Exception as e:
        wrap_exception(env, e)
        return NULL


cdef public jboolean Java_com_chaquo_python_PyObject_equals \
    (JNIEnv *env, jobject this, jobject that) with gil:
    try:
        raise Exception() # FIXME
    except Exception as e:
        wrap_exception(env, e)
        return False


cdef public jstring Java_com_chaquo_python_PyObject_toString \
    (JNIEnv *env, jobject this) with gil:
    return to_string(env, this, str)

cdef public jstring Java_com_chaquo_python_PyObject_repr \
    (JNIEnv *env, jobject this) with gil:
    return to_string(env, this, repr)

cdef jstring to_string(JNIEnv *env, jobject this, func):
    try:
        self = j2p_pyobject(env, this)
        result =  p2j_string(env, func(self))
        return env[0].NewLocalRef(env, result.obj)
    except Exception as e:
        wrap_exception(env, e)
        return NULL


cdef public jint Java_com_chaquo_python_PyObject_hashCode \
    (JNIEnv *env, jobject this) with gil:
    try:
        return hash(j2p_pyobject(env, this)) & 0x7FFFFFFF
    except Exception as e:
        wrap_exception(env, e)
        return 0

# =============================================================================

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
