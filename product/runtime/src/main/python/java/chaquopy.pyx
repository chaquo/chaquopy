from __future__ import absolute_import, division, print_function

from collections import defaultdict

cdef extern from "alloca.h":
    void *alloca(size_t size)

cdef extern from "Python.h":
    void PyEval_InitThreads()

__all__ = ['JavaException', 'cast', 'detach']


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
