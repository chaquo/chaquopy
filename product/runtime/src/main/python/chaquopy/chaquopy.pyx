# FIXME: survey all <...> casts without question mark, and remove or add question mark.

from collections import defaultdict

# FIXME remove this cimport, and replace malloc/free with alloca everywhere.
from libc.stdlib cimport malloc, free
cdef extern from "alloca.h":
    void *alloca(size_t size)

cdef extern from "Python.h":
    void PyEval_InitThreads()

__all__ = ['JavaObject', 'JavaMethod', 'JavaField',
           'JavaClass', 'JavaException', 'cast', 'find_javaclass',
           'PythonJavaClass', 'java_method', 'detach']


# PyEval_InitThreads() is called by all Cython-generated module initialization functions, but
# in case that changes, let's make absolutely sure.
PyEval_InitThreads()

telem = defaultdict(int)

# TODO #5148
DEF JNIUS_PYTHON3 = False

from jni cimport *
include "env.pxi"
include "jvm.pxi"
include "utils.pxi"
include "conversion.pxi"
include "class.pxi"
include "proxy.pxi"
