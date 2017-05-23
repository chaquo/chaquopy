# FIXME Rename top-level chaquopy module to java

from __future__ import absolute_import, division, print_function

# On Android, the native module is stored separately to the Python modules.
from pkgutil import extend_path
__path__ = extend_path(__path__, __name__)

from .chaquopy import *  # noqa
from .signatures import *  # noqa
from .reflect import *  # noqa

# jvoid is not in the public API because the user would have no use for it.
__all__ = ["autoclass", "cast", "detach", "JavaException",
           "jboolean", "jbyte", "jshort", "jint", "jlong", "jfloat", "jdouble", "jchar",
           "jarray"]


# TODO #5167 test this. I don't see any reason why it has to be Android-specific, though maybe
# it's only Android which enforces it.
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
