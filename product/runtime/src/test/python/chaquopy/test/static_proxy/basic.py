from __future__ import absolute_import, division, print_function

from java import constructor, method, static_proxy, jint
from ..pyobjecttest import DelTrigger


class BasicAdder(static_proxy()):
    @constructor([jint])
    def __init__(self, n):
        super(BasicAdder, self).__init__()
        self.n = n

    @method(jint, [jint])
    def add(self, x):
        return self.n + x


class GC(static_proxy()):
    @constructor([])
    def __init__(self):
        super(GC, self).__init__()
        self.dt = DelTrigger()
