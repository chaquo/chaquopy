# FIXME: survey all <...> casts without question mark, and remove or add question mark.

__all__ = ('JavaClass', 'JavaMethod', 'JavaField',
           'MetaJavaClass', 'JavaException', 'cast', 'find_javaclass',
           'PythonJavaClass', 'java_method', 'detach')

from collections import defaultdict

from libc.stdlib cimport malloc, free


telem = defaultdict(int)


include "jni.pxi"
include "config.pxi"

IF JNIUS_PLATFORM == "android":
    include "jnius_jvm_android.pxi"
ELIF JNIUS_PLATFORM in ("win32", "cygwin"):
    include "jnius_jvm_desktop.pxi"
ELSE:
    include "jnius_jvm_dlopen.pxi"

include "jnius_env.pxi"
include "jnius_utils.pxi"
include "jnius_conversion.pxi"
include "jnius_localref.pxi"
include "jnius_export_func.pxi"
include "jnius_export_class.pxi"
include "jnius_proxy.pxi"
