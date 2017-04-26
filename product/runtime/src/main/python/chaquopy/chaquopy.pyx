# FIXME: survey all <...> casts without question mark, and remove or add question mark.

__all__ = ('JavaClass', 'JavaMethod', 'JavaField',
           'MetaJavaClass', 'JavaException', 'cast', 'find_javaclass',
           'PythonJavaClass', 'java_method', 'detach')

from collections import defaultdict

# FIXME remove this cimport, and replace malloc/free with alloca everywhere.
from libc.stdlib cimport malloc, free
cdef extern from "alloca.h":
    void *alloca(size_t size)


telem = defaultdict(int)

# TODO #5148
DEF JNIUS_PYTHON3 = False

include "jni.pxi"
include "utils.pxi"
include "conversion.pxi"
include "class.pxi"
include "proxy.pxi"
