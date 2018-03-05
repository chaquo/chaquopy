#cython: binding=True, nonecheck=False, profile=False

from __future__ import absolute_import, division, print_function

# Workaround for https://github.com/cython/cython/issues/1720, which should ultimately be fixed
# by https://github.com/cython/cython/issues/1715
__package__ = "java"

cdef extern from "chaquopy_extra.h":
    pass


# Imports used in this file
cdef extern from "Python.h":
    void PyEval_InitThreads()


# Imports used in multiple files
from collections import OrderedDict
import os
import sys
import threading

import java
from java._vendor import six

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
        java.detach()

b_i = ("_Thread__bootstrap_inner" if hasattr(threading.Thread, "_Thread__bootstrap_inner")
       else "_bootstrap_inner")
Thread_bootstrap_inner_original = getattr(threading.Thread, b_i)
setattr(threading.Thread, b_i, Thread_bootstrap_inner)


from .jni cimport *
include "utils.pxi"
include "exception.pxi"
include "env.pxi"
include "jvm.pxi"
include "conversion.pxi"
include "class.pxi"
include "proxy.pxi"
include "array.pxi"
include "import.pxi"
include "license.pxi"


def chaquopy_init():
    if "CHAQUOPY_PROCESS_TYPE" not in os.environ:  # See chaquopy_java.pyx
        os.environ["CHAQUOPY_PROCESS_TYPE"] = "python"
        set_jvm(start_jvm())

        platform = java.jclass("com.chaquo.python.GenericPlatform")()
        java.jclass("com.chaquo.python.Python").start(platform)
