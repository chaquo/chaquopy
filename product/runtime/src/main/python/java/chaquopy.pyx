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

__all__ = ['cast', 'detach', 'JavaException', 'jklass']


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
