# FIXME: survey all <...> casts without question mark, and remove or add question mark.

__all__ = ('JavaClass', 'JavaMethod', 'JavaField',
           'MetaJavaClass', 'JavaException', 'cast', 'find_javaclass',
           'PythonJavaClass', 'java_method', 'detach')

from collections import defaultdict

from libc.stdlib cimport malloc, free


telem = defaultdict(int)

# TODO #5148
DEF JNIUS_PYTHON3 = False

# FIXME remove
DEF JNIUS_PLATFORM = 'cygwin'

include "jni.pxi"

IF JNIUS_PLATFORM == "android":
    include "jvm_android.pxi"
ELIF JNIUS_PLATFORM in ("win32", "cygwin"):
    include "jvm_desktop.pxi"
ELSE:
    include "jvm_dlopen.pxi"

include "env.pxi"
include "utils.pxi"
include "conversion.pxi"
include "localref.pxi"
include "func.pxi"
include "class.pxi"
include "proxy.pxi"
