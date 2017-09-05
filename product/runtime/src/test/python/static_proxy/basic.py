# FIXME:
#
# Bases
# Overloaded methods
# Overloaded constructors
# Return conversions
# Exceptions
#
# Construction from both languages
# Conversion in both directions
# Garbage collection
# Call base class methods and read/write fields
# Access protected members
# Any other things which work differently to dynamic proxies
# toJava:“If the Python object is itself a proxy for a Java object of a compatible type, the
#   original Java object will be returned.”
#
# Use manually-generated Java to test:
# * mismatched extends or implements
# * if class implements StaticProxy then the base JavaClass metaclass should refuse to reflect
#   it: means things have been loaded in the wrong order.


from __future__ import absolute_import, division, print_function

from java import *
from java.lang import String

class BasicAdder(static_proxy()):
    @constructor([jint])
    def __init__(self, n):
        self.n = n

    @method(jint, [jint])
    def add(self, x):
        return self.n + x


class OverloadedAdder(static_proxy()):
    @method(jint, [jint, jint])
    @method(jdouble, [jdouble, jdouble])
    @method(String, [String, String])
    def add(self, a, b):
        return a + b


class OverloadedCtor(static_proxy()):
    @constructor([])
    @constructor([jint])
    @constructor([String])
    def __init__(self, value=None):
        self.value = str(value)

    @method(String, [])
    def get(self):
        return self.value


