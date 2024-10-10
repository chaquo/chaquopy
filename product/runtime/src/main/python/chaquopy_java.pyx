# cython: language_level=2

# __future__ import may still be required as long as we have language_level=2.
from __future__ import absolute_import, division, print_function

import ctypes
from importlib import import_module
import os
import sys
import traceback

from cpython.module cimport PyImport_ImportModule
from cpython.object cimport PyObject
from cpython.ref cimport Py_DECREF
cdef extern from "Python.h":
    void Py_Initialize()
    void PyEval_SaveThread()

from libc.errno cimport errno
from libc.stdint cimport uintptr_t
from libc.stdlib cimport getenv, malloc
from libc.stdio cimport printf, snprintf
from libc.string cimport strerror, strlen
from posix.stdlib cimport putenv

import java
from java.jni cimport *
from java.chaquopy cimport *
cdef extern from "chaquopy_java_extra.h":
    void PyInit_chaquopy_java() except *


cdef public jint JNI_OnLoad(JavaVM *jvm, void *reserved) noexcept:
    return JNI_VERSION_1_6


# === com.chaquo.python.Python ================================================

# This runs before Py_Initialize, so it must compile to pure C.
cdef public void Java_com_chaquo_python_Python_startNative(
    JNIEnv *env, jobject klass, jobject j_platform, jobject j_python_path
) noexcept:
    if getenv("CHAQUOPY_PROCESS_TYPE") == NULL:  # See jvm.pxi
        startNativeJava(env, j_platform, j_python_path)
    else:
        init_module(env)


# We're running in a Java process, so start the Python VM.
cdef void startNativeJava(
    JNIEnv *env, jobject j_platform, jobject j_python_path
) noexcept:
    cdef const char *python_path
    if j_python_path != NULL:
        python_path = env[0].GetStringUTFChars(env, j_python_path, NULL)
        if python_path == NULL:
            throw_simple_exception(env, "GetStringUTFChars failed in startNativeJava")
            return
        try:
            if not set_env(env, "PYTHONPATH", python_path):
                return
            if not set_env(env, "CHAQUOPY_PROCESS_TYPE", "java"):  # See chaquopy.pyx
                return
        finally:  # Yes, this does compile to pure C, with the help of "goto".
            env[0].ReleaseStringUTFChars(env, j_python_path, python_path)

    Py_Initialize()  # Calls abort() on failure

    # All code run before Py_Initialize must compile to pure C. After Py_Initialize returns we
    # can start using the Python VM, but many things will still cause a native crash until our
    # module initialization function succeeds. In particular, global and built-in names won't
    # be bound, and "import" won't work either, even locally.
    if not init_module(env):
        return  # A Java exception should already have been thrown.

    cdef SavedException se = None
    cdef JavaVM *jvm = NULL
    try:
        ret = env[0].GetJavaVM(env, &jvm)
        if ret != 0:
             raise Exception(f"GetJavaVM failed: {ret}")
        set_jvm(jvm)
    except BaseException:
        se = SavedException()
    if se:
        se.throw(env)

    # We imported java.chaquopy above, which has called PyEval_InitThreads during its own
    # module intialization, so the GIL now exists and we have it. We must release the GIL
    # before we return to Java so that the methods below can be called from any thread.
    # (http://bugs.python.org/issue1720250)
    PyEval_SaveThread()


# WARNING: This function (specifically PyInit_chaquopy_java) will crash if called
# more than once.
cdef bint init_module(JNIEnv *env) noexcept with gil:
    try:
        # See CYTHON_PEP489_MULTI_PHASE_INIT in chaquopy_java_extra.h.
        PyInit_chaquopy_java()
        return True
    except BaseException:
        throw_simple_exception(env, format_exception().encode("utf-8"))
        return False


# The POSIX setenv function is not available on MSYS2.
# This runs before Py_Initialize, so it must compile to pure C.
cdef bint set_env(JNIEnv *env, const char *name, const char *value) noexcept:
    cdef int putenvArgLen = strlen(name) + 1 + strlen(value) + 1
    cdef char *putenvArg = <char*>malloc(putenvArgLen)
    if snprintf(putenvArg, putenvArgLen, "%s=%s", name, value) != (putenvArgLen - 1):
        throw_simple_exception(env, "snprintf failed in set_env")
        return False

    # putenv takes ownership of the string passed to it.
    if putenv(putenvArg) != 0:
        throw_simple_exception(env, "putenv failed in set_env")
        return False

    return True


cdef public jlong Java_com_chaquo_python_Python_getModuleNative \
    (JNIEnv *env, jobject this, jobject j_name) noexcept with gil:
    try:
        return p2j_pyobject(env, import_module(j2p_string(env, LocalRef.create(env, j_name))))
    except BaseException:
        se = SavedException()
    se.throw(env)
    return 0


# === com.chaquo.python.PyObject ==============================================

cdef public void Java_com_chaquo_python_PyObject_closeNative \
    (JNIEnv *env, jobject this) noexcept with gil:
    try:
        Py_DECREF(j2p_pyobject(env, this))  # Matches with INCREF in p2j_pyobject.
        return
    except BaseException:
        se = SavedException()
    se.throw(env)


cdef public jlong Java_com_chaquo_python_PyObject_fromJavaNative \
    (JNIEnv *env, jobject klass, jobject o) noexcept with gil:
    try:
        return p2j_pyobject(env, j2p(env, LocalRef.create(env, o)))
    except BaseException:
        se = SavedException()
    se.throw(env)
    return 0


cdef public jobject Java_com_chaquo_python_PyObject_toJava \
    (JNIEnv *env, jobject this, jobject to_klass) noexcept with gil:
    try:
        self = j2p_pyobject(env, this)
        if not to_klass:
            se = SavedException("java.lang.NullPointerException")
        else:
            to_sig = box_sig(env, LocalRef.create(env, to_klass))
            try:
                return (<JNIRef?>p2j(env, to_sig, self)).return_ref(env)
            except TypeError:
                se = SavedException("java.lang.ClassCastException")
    except BaseException:
        se = SavedException()
    se.throw(env)
    return NULL


# Many of these primitive conversion functions are identical apart from the type code, but they
# can't simply call a common function, because the main return statement has to be inside a
# SavedException try block in case of numeric overflow.
cdef public jboolean Java_com_chaquo_python_PyObject_toBoolean \
    (JNIEnv *env, jobject this) noexcept with gil:
    try:
        self = j2p_pyobject(env, this)
        try:
            return p2j(env, "Z", self)
        except TypeError:
            se = SavedException("java.lang.ClassCastException")
    except BaseException:
        se = SavedException()
    se.throw(env)
    return 0

cdef public jbyte Java_com_chaquo_python_PyObject_toByte \
    (JNIEnv *env, jobject this) noexcept with gil:
    try:
        self = j2p_pyobject(env, this)
        try:
            return p2j(env, "B", self)
        except TypeError:
            se = SavedException("java.lang.ClassCastException")
    except BaseException:
        se = SavedException()
    se.throw(env)
    return 0

cdef public jchar Java_com_chaquo_python_PyObject_toChar \
    (JNIEnv *env, jobject this) noexcept with gil:
    try:
        self = j2p_pyobject(env, this)
        try:
            result = p2j(env, "C", self)
        except TypeError:
            se = SavedException("java.lang.ClassCastException")
        else:
            check_range_char(result)
            return ord(result)
    except BaseException:
        se = SavedException()
    se.throw(env)
    return 0

cdef public jshort Java_com_chaquo_python_PyObject_toShort \
    (JNIEnv *env, jobject this) noexcept with gil:
    try:
        self = j2p_pyobject(env, this)
        try:
            return p2j(env, "S", self)
        except TypeError:
            se = SavedException("java.lang.ClassCastException")
    except BaseException:
        se = SavedException()
    se.throw(env)
    return 0

cdef public jint Java_com_chaquo_python_PyObject_toInt \
    (JNIEnv *env, jobject this) noexcept with gil:
    try:
        self = j2p_pyobject(env, this)
        try:
            return p2j(env, "I", self)
        except TypeError:
            se = SavedException("java.lang.ClassCastException")
    except BaseException:
        se = SavedException()
    se.throw(env)
    return 0

cdef public jlong Java_com_chaquo_python_PyObject_toLong \
    (JNIEnv *env, jobject this) noexcept with gil:
    try:
        self = j2p_pyobject(env, this)
        try:
            return p2j(env, "J", self)
        except TypeError:
            se = SavedException("java.lang.ClassCastException")
    except BaseException:
        se = SavedException()
    se.throw(env)
    return 0

cdef public jfloat Java_com_chaquo_python_PyObject_toFloat \
    (JNIEnv *env, jobject this) noexcept with gil:
    try:
        self = j2p_pyobject(env, this)
        try:
            result = p2j(env, "F", self)
        except TypeError:
            se = SavedException("java.lang.ClassCastException")
        else:
            check_range_float32(result)
            return result
    except BaseException:
        se = SavedException()
    se.throw(env)
    return 0

cdef public jdouble Java_com_chaquo_python_PyObject_toDouble \
    (JNIEnv *env, jobject this) noexcept with gil:
    try:
        self = j2p_pyobject(env, this)
        try:
            return p2j(env, "D", self)
        except TypeError:
            se = SavedException("java.lang.ClassCastException")
    except BaseException:
        se = SavedException()
    se.throw(env)
    return 0

cdef public jlong Java_com_chaquo_python_PyObject_id \
    (JNIEnv *env, jobject this) noexcept with gil:
    try:
        return id(j2p_pyobject(env, this))
    except BaseException:
        se = SavedException()
    se.throw(env)
    return 0


cdef public jlong Java_com_chaquo_python_PyObject_typeNative \
    (JNIEnv *env, jobject this) noexcept with gil:
    try:
        return p2j_pyobject(env, type(j2p_pyobject(env, this)))
    except BaseException:
        se = SavedException()
    se.throw(env)
    return 0


cdef public jlong Java_com_chaquo_python_PyObject_callThrowsNative \
    (JNIEnv *env, jobject this, jobject jargs) noexcept with gil:
    try:
        return call(env, j2p_pyobject(env, this), jargs)
    except BaseException:
        se = SavedException()
    se.throw(env)
    return 0


# It's worth making this a native method in order to avoid the temporary PyObject which would
# be created by `get(name).call(...)`.
cdef public jlong Java_com_chaquo_python_PyObject_callAttrThrowsNative \
    (JNIEnv *env, jobject this, jobject j_key, jobject jargs) noexcept with gil:
    try:
        attr = getattr(j2p_pyobject(env, this),
                       j2p_string(env, LocalRef.create(env, j_key)))
        return call(env, attr, jargs)
    except BaseException:
        se = SavedException()
    se.throw(env)
    return 0


cdef jlong call(JNIEnv *j_env, obj, jobject jargs) except? 0:
    if jargs == NULL:
        # User typed ".call(null)", which Java interprets as a null array, rather than the
        # array of one null which they intended.
        all_args = [None]
    else:
        all_args = java.jarray("Ljava/lang/Object;")(instance=LocalRef.create(j_env, jargs))

    Kwarg = java.jclass("com.chaquo.python.Kwarg")
    args = []
    kwargs = {}
    for a in all_args:
        if isinstance(a, Kwarg):
            if a.key in kwargs:
                raise SyntaxError(f"keyword argument repeated: '{a.key}'")
            kwargs[a.key] = a.value
        else:
            if kwargs:
                raise SyntaxError("positional argument follows keyword argument")
            args.append(a)

    return p2j_pyobject(j_env, obj(*args, **kwargs))


# === com.chaquo.python.PyObject (Map) ========================================

cdef public jboolean Java_com_chaquo_python_PyObject_containsKeyNative \
    (JNIEnv *env, jobject this, jobject j_key) noexcept with gil:
    try:
        self = j2p_pyobject(env, this)
        key = j2p_string(env, LocalRef.create(env, j_key))
        return hasattr(self, key)
    except BaseException:
        se = SavedException()
    se.throw(env)
    return False


cdef public jlong Java_com_chaquo_python_PyObject_getNative \
    (JNIEnv *env, jobject this, jobject j_key) noexcept with gil:
    try:
        self = j2p_pyobject(env, this)
        key = j2p_string(env, LocalRef.create(env, j_key))
        try:
            value = getattr(self, key)
        except AttributeError:
            return 0
        return p2j_pyobject(env, value)
    except BaseException:
        se = SavedException()
    se.throw(env)
    return 0


cdef public jlong Java_com_chaquo_python_PyObject_putNative \
    (JNIEnv *env, jobject this, jobject j_key, jobject j_value) noexcept with gil:
    try:
        self = j2p_pyobject(env, this)
        key = j2p_string(env, LocalRef.create(env, j_key))
        try:
            old_value = getattr(self, key)
        except AttributeError:
            old_value = None
        setattr(self, key, j2p(env, LocalRef.create(env, j_value)))
        return p2j_pyobject(env, old_value)
    except BaseException:
        se = SavedException()
    se.throw(env)
    return 0


cdef public jlong Java_com_chaquo_python_PyObject_removeNative \
    (JNIEnv *env, jobject this, jobject j_key) noexcept with gil:
    try:
        self = j2p_pyobject(env, this)
        key = j2p_string(env, LocalRef.create(env, j_key))
        try:
            old_value = getattr(self, key)
        except AttributeError:
            return 0
        delattr(self, key)
        return p2j_pyobject(env, old_value)
    except BaseException:
        se = SavedException()
    se.throw(env)
    return 0


cdef public jobject Java_com_chaquo_python_PyObject_dir \
    (JNIEnv *env, jobject this) noexcept with gil:
    try:
        keys = java.jclass("java.util.ArrayList")()
        for key in dir(j2p_pyobject(env, this)):
            keys.add(key)
        return (<JNIRef?>keys._chaquopy_this).return_ref(env)
    except BaseException:
        se = SavedException()
    se.throw(env)
    return NULL

# === com.chaquo.python.PyObject (Object) =====================================

cdef public jboolean Java_com_chaquo_python_PyObject_equals \
    (JNIEnv *env, jobject this, jobject that) noexcept with gil:
    try:
        return j2p_pyobject(env, this) == j2p(env, LocalRef.create(env, that))
    except BaseException:
        se = SavedException()
    se.throw(env)
    return False


cdef public jobject Java_com_chaquo_python_PyObject_toString \
    (JNIEnv *env, jobject this) noexcept with gil:
    return to_string(env, this, str)

cdef public jobject Java_com_chaquo_python_PyObject_repr \
    (JNIEnv *env, jobject this) noexcept with gil:
    return to_string(env, this, repr)

cdef jobject to_string(JNIEnv *env, jobject this, func):
    try:
        self = j2p_pyobject(env, this)
        return p2j_string(env, func(self)).return_ref(env)
    except BaseException:
        se = SavedException()
    se.throw(env)
    return NULL


cdef public jint Java_com_chaquo_python_PyObject_hashCode \
    (JNIEnv *env, jobject this) noexcept with gil:
    try:
        self = j2p_pyobject(env, this)
        return ctypes.c_int32(hash(self)).value
    except BaseException:
        se = SavedException()
    se.throw(env)
    return 0


# === Exception handling ======================================================

# Use `DEF` rather than `cdef const` because the latter may not be initialized after module
# initialization failure.
DEF fqn_PyException_b = b"com/chaquo/python/PyException"
fqn_PyException = fqn_PyException_b.decode()


# See note at convert_exception for why local `jclass` proxy objects must be destroyed before
# calling JNIEnv.Throw. If the exception was a Java exception, this includes the proxy object
# for the exception itself. exc_info() is cleared automatically when the `except` block
# terminates, so we save the exception within the `except` block, and call JNIEnv.Throw outside
# it. This can't be done with a context manager because the system would still have its own
# reference to the exception while the __exit__ method was running.
cdef class SavedException(object):
    cdef exc_info
    cdef java_cls_name

    def __init__(self, java_cls_name=None):
        self.exc_info = sys.exc_info()
        self.java_cls_name = java_cls_name

    cdef throw(self, JNIEnv *env):
        formatted_exc = format_exception(self.exc_info)
        try:
            j_exc = convert_exception(env, self.exc_info, self.java_cls_name)
            self.exc_info = None
            ret = env[0].Throw(env, j_exc.obj)
            if ret != 0:
                raise Exception(f"Throw failed: {ret}")
        except BaseException:
            msg = f"{formatted_exc}\n[failed to merge stack traces: {format_exception()}]"
            self.exc_info = None
            throw_simple_exception(env, msg.encode("utf-8"))


# This is broken out into a separate method to make sure all of its local `jclass` and `jarray`
# proxy objects are destroyed before JNIEnv.Throw is called. This is necessary because removal
# from instance_cache calls JNIRef.__hash__, which may call Object.identityHashCode, which
# Android's CheckJNI will not allow with an exception pending. Caching the hash code should
# reduce the risk of this, but I'm not totally confident that it covers all cases.
#
# If java_cls_name is not None, this function returns a new Java exception of that class.
# Otherwise, if exc_info refers to a Java exception, it will be returned with a modified stack
# trace. Otherwise, a new PyException will be returned.
cdef JNIRef convert_exception(JNIEnv *env, exc_info, java_cls_name):
    _, exc_value, exc_traceback = exc_info
    python_trace = tb_to_java(exc_traceback) if exc_traceback else []

    Throwable = java.jclass("java.lang.Throwable")
    if isinstance(exc_value, Throwable) and java_cls_name is None:
        java_exc = exc_value
        pre_trace = Throwable().getStackTrace()
        post_trace = list(java_exc.getStackTrace())[:-len(pre_trace)]
        java_exc.setStackTrace(post_trace + python_trace + pre_trace)
    else:
        java_cls = java.jclass(java_cls_name or fqn_PyException)
        java_exc = java_cls(format_exception_only(exc_value) if exc_value else "")
        java_exc.setStackTrace(python_trace + java_exc.getStackTrace())
    return java_exc._chaquopy_this


# Converts a Python traceback to a list of StackTraceElements which can be passed to
# Throwable.setStackTrace.
def tb_to_java(tb):
    result = []
    StackTraceElement = java.jclass("java.lang.StackTraceElement")
    for frame, line_no in traceback.walk_tb(tb):
        code = frame.f_code
        # We only include the basename of the Python source file, because Google Play crash
        # reports omit stack frames with slashes in their filenames. Also, this makes Python
        # source line numbers clickable in the Android Studio Logcat window.
        filename = os.path.basename(code.co_filename)

        # The Python module name will become the Java class name. It's not easy to get the
        # actual Python class name, if any, because __qualname__ is an attribute of the
        # function, not the code object (https://stackoverflow.com/a/14821336).
        mod_name = frame.f_globals.get("__name__", "")

        # Cython function names contain a module name prefix. Even if this is fixed for our
        # modules by a new version of Cython, most third-party sdists contain pre-generated .c
        # files, so it wouldn't be fixed for them.
        func_name = code.co_name
        mod_prefix = mod_name + "."
        if func_name.startswith(mod_prefix):
            func_name = func_name[len(mod_prefix):]

        result.append(StackTraceElement("<python>." + mod_name, func_name, filename, line_no))

    result.reverse()
    return result

# Unlike the `traceback` function of the same name, this function returns a single string.
# May be called after module initialization failure (see note after call to Py_Initialize).
cdef format_exception(exc_info=None):
    e = None
    try:
        if exc_info is None:
            sys = PyImport_ImportModule("sys")
            exc_info = sys.exc_info()
        e = exc_info[1]
        traceback = PyImport_ImportModule("traceback")
        return "".join(traceback.format_exception(*exc_info)).strip()
    except BaseException as e2:
        return (f"{format_exception_only(e)} [failed to format Python stack trace: "
                f"{format_exception_only(e2)}]")


# Unlike the `traceback` function of the same name, this function returns a single string.
# May be called after module initialization failure (see note after call to Py_Initialize).
cdef format_exception_only(e):
    return f"{type(e).__name__}: {e}"


# This may run before Py_Initialize, so it must compile to pure C.
cdef void throw_simple_exception(JNIEnv *env, const char *message):
    j_exc_klass = env[0].FindClass(env, fqn_PyException_b)
    if j_exc_klass == NULL:
        printf("%s [FindClass failed in throw_simple_exception]\n", message)
        return
    ret = env[0].ThrowNew(env, j_exc_klass, message)
    if ret != 0:
        printf("%s [ThrowNew failed in throw_simple_exception: %d]\n", message, ret)
    # No need to release local references: if we're throwing a Java exception then we must be
    # imminently returning from a `native` method.
