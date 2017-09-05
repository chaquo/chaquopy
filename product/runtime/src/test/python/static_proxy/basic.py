# FIXME:
#
# Garbage collection
# Any other things which work differently to dynamic proxies
# toJava: "If the Python object is itself a proxy for a Java object of a compatible type, the
#   original Java object will be returned."
#
# Fix swallowed exception when referencing StaticProxy from JavaClass.__new__

from __future__ import absolute_import, division, print_function

from java import *


class BasicAdder(static_proxy()):
    @constructor([jint])
    def __init__(self, n):
        super(BasicAdder, self).__init__()
        self.n = n

    @method(jint, [jint])
    def add(self, x):
        return self.n + x
