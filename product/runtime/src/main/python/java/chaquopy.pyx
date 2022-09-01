# cython: language_level=2, binding=True, nonecheck=False, profile=False
#
# `binding=True` because we assign some methods to a class dictionary, e.g. Throwable_str.
# (This currently affects profiling results: see https://github.com/cython/cython/issues/2137.)
#
# `nonecheck` may catch some programming errors which would otherwise cause a native crash, but
# is too expensive to leave on all the time.
#
# `profile` reports entry and exit of all Cython functions to the Python profiling system, but
# is too expensive to leave on all the time.

# __future__ import may still be required as long as we have language_level=2.
from __future__ import absolute_import, division, print_function

# Workaround for https://github.com/cython/cython/issues/1720, which should ultimately be fixed
# by https://github.com/cython/cython/issues/1715
__package__ = "java"

cdef extern from "chaquopy_extra.h":
    pass


# Imports used in this file
from threading import Thread

cdef extern from "Python.h":
    void PyEval_InitThreads()


# Imports used in multiple files
from collections import OrderedDict
import os
import sys

from java import primitive
from java.primitive import (Primitive, NumericPrimitive, IntPrimitive, FloatPrimitive,
                            primitives_by_name, primitives_by_sig)

cimport cython
cdef extern from "alloca.h":
    void *alloca(size_t size)


__all__ = [
    "chaquopy_init",
    "detach",                                                              # jvm.pxi
    "cast",                                                                # utils.pxi
    "jclass",                                                              # class.pxi
    "dynamic_proxy", "static_proxy", "constructor", "method", "Override",  # proxy.pxi
    "jarray",                                                              # array.pxi
    "set_import_enabled",                                                  # import.pxi
]


# Multi-threading is always enabled in Java.
PyEval_InitThreads()

# Monkey-patching this internal method isn't ideal, but we want to detach as late as possible
# in order to avoid accidental reattachment, even if the thread is terminated by a Java
# exception.
def Thread_bootstrap_inner(self):
    try:
        Thread_bootstrap_inner_original(self)
    finally:
        detach()

b_i = ("_Thread__bootstrap_inner" if hasattr(Thread, "_Thread__bootstrap_inner")
       else "_bootstrap_inner")
Thread_bootstrap_inner_original = getattr(Thread, b_i)
setattr(Thread, b_i, Thread_bootstrap_inner)


from .jni cimport *
include "utils.pxi"
include "signature.pxi"
include "exception.pxi"
include "env.pxi"
include "jvm.pxi"
include "conversion.pxi"
include "class.pxi"
include "overload.pxi"
include "proxy.pxi"
include "array.pxi"
include "import.pxi"
include "android.pxi"

def chaquopy_init():
    if "CHAQUOPY_PROCESS_TYPE" not in os.environ:  # See chaquopy_java.pyx
        os.environ["CHAQUOPY_PROCESS_TYPE"] = "python"
        set_jvm(start_jvm())

        platform = jclass("com.chaquo.python.GenericPlatform")()
        jclass("com.chaquo.python.Python").start(platform)
