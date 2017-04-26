from .chaquopy import *  # noqa
from .reflect import *  # noqa

# XXX monkey patch methods that cannot be in cython.
# Cython doesn't allow to set new attribute on methods it compiled

HASHCODE_MAX = 2 ** 31 - 1


class PythonJavaClass_(PythonJavaClass):

    @java_method('()I', name='hashCode')
    def hashCode(self):
        return id(self) % HASHCODE_MAX

    @java_method('()Ljava/lang/String;', name='hashCode')
    def hashCode_(self):
        return '{}'.format(self.hashCode())

    @java_method('()Ljava/lang/String;', name='toString')
    def toString(self):
        return repr(self)

    @java_method('(Ljava/lang/Object;)Z', name='equals')
    def equals(self, other):
        return self.hashCode() == other.hashCode()


PythonJavaClass = PythonJavaClass_

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
