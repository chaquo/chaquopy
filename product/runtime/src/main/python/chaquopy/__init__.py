# FIXME Rename top-level chaquopy module to java
#
# FIXME define __all__ as follows:
#   jclass (autoclass)
#   cast
#   JavaException
#   detach

#   jbyte, jshort, jint, jlong (truncate=False)
#   jfloat, jdouble
#   jchar
#   jboolean (will just call bool())
#
#   These functions can be used to wrap a method parameter to specify its Java primitive type.
#
#   Java has more primitive types than Python, so where more than one compatible integer or
#   floating-point overload is available for a method call, the widest one will be used by
#   default. Similarly, where an overload is available for both `String` and `char`, `String`
#   will be used. If this behavior gives undesired results, these functions can be used to
#   override it.
#
#   For example, if `p` is a `PrintStream`, `p.print(42)` will call `print(long)`, whereas
#   `p.print(jint(42))` will call `print(int)`. Likewise, `p.print("x")` will call
#   `print(String)`, while `p.print(jchar("x"))` will call `print(char)`.
#
#   The integral type functions take an optional `truncate` parameter. If this is true, any
#   excess high-order bits of the given value will be discarded. Otherwise, an out-of-range
#   value will result in an exception.
#
#   The object types returned by these functions are not specified, but are guaranteed to be
#   accepted by compatible Java method calls and field assignments.


from __future__ import absolute_import, division, print_function

# On Android, the native module is stored separately to the Python modules.
from pkgutil import extend_path
__path__ = extend_path(__path__, __name__)

from .chaquopy import *  # noqa
from .reflect import *  # noqa


# FIXME check this
# from https://gist.github.com/tito/09c42fb4767721dc323d
import os
if "ANDROID_ARGUMENT" in os.environ:
    # on android, catch all exception a detach
    import threading
    import chaquopy
    orig_thread_run = threading.Thread.run

    def cqp_thread_hook(*args, **kwargs):
        try:
            return orig_thread_run(*args, **kwargs)
        finally:
            chaquopy.detach()

    threading.Thread.run = cqp_thread_hook
