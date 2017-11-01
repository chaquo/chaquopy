#cython: binding=True, nonecheck=False

from __future__ import absolute_import, division, print_function

cdef extern from "chaquopy_extra.h":
    pass

# Imports used in this file
from collections import defaultdict
import threading
cdef extern from "Python.h":
    void PyEval_InitThreads()

# Imports used in multiple .pxi files
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

# Overriding Thread.run via __getattribute__ is the only option I can think of which allows us
# to also affect Thread subclasses which don't call up to the base class implementation.
Thread_getattribute_original = threading.Thread.__getattribute__

def Thread_getattribute(self, name):
    if name == "run":
        run_original = Thread_getattribute_original(self, name)
        def run():
            run_original()
            java.detach()
        return run
    else:
        return Thread_getattribute_original(self, name)

threading.Thread.__getattribute__ = Thread_getattribute


# TODO #5148
DEF JNIUS_PYTHON3 = False

from .jni cimport *
include "env.pxi"
include "jvm.pxi"
include "utils.pxi"
include "exception.pxi"
include "conversion.pxi"
include "class.pxi"
include "proxy.pxi"
include "array.pxi"
include "import.pxi"

def chaquopy_init():
    if "CHAQUOPY_PROCESS_TYPE" not in os.environ:  # See chaquopy_java.pyx
        os.environ["CHAQUOPY_PROCESS_TYPE"] = "python"
        set_jvm(start_jvm())

        platform = java.jclass("com.chaquo.python.GenericPlatform")()
        java.jclass("com.chaquo.python.Python").start(platform)
