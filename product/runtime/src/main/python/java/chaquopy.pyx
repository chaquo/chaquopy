from __future__ import absolute_import, division, print_function

cdef extern from "chaquopy_extra.h":
    pass

# Imports used in this file
from collections import defaultdict
cdef extern from "Python.h":
    void PyEval_InitThreads()

# Imports used in multiple .pxi files
import java
from java._vendor import six
cdef extern from "alloca.h":
    void *alloca(size_t size)

__all__ = [
    "chaquopy_init",
    "detach",                           # jvm.pxi
    "cast", "JavaException",            # utils.pxi
    "jklass",                           # class.pxi
    "set_import_enabled",               # import.pxi
]


# Multi-threading is unavoidable in Java.
PyEval_InitThreads()

telem = defaultdict(int)

# TODO #5148
DEF JNIUS_PYTHON3 = False

from .jni cimport *
include "env.pxi"
include "jvm.pxi"
include "utils.pxi"
include "conversion.pxi"
include "class.pxi"
include "array.pxi"
include "import.pxi"

def chaquopy_init():
    if "CHAQUOPY_PROCESS_TYPE" not in os.environ:  # See chaquopy_java.pyx
        os.environ["CHAQUOPY_PROCESS_TYPE"] = "python"
        set_jvm(start_jvm())

        platform = java.jclass("com.chaquo.python.GenericPlatform")()
        java.jclass("com.chaquo.python.Python").start(platform)
