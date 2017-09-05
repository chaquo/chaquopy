# FIXME:
#
# Exceptions
# Modifiers??
#
# Construction from both languages
# Conversion in both directions
# Garbage collection
# Any other things which work differently to dynamic proxies
# toJava: "If the Python object is itself a proxy for a Java object of a compatible type, the
#   original Java object will be returned."
#
# Use manually-generated Java to test:
# * mismatched extends or implements
# * if class implements StaticProxy then the base JavaClass metaclass should refuse to reflect
#   it: means things have been loaded in the wrong order.


from __future__ import absolute_import, division, print_function

from java import *
from java.lang import String
from com.chaquo.java import StaticProxyTest as SPT


class BasicAdder(static_proxy()):
    @constructor([jint])
    def __init__(self, n):
        self.n = n

    @method(jint, [jint])
    def add(self, x):
        return self.n + x


class OtherPackage(static_proxy(package="other.pkg")):
    @method(String, [])
    def hello(self):
        return "world"


class Ca(static_proxy(SPT.ClassA)): pass
class Ia(static_proxy(None, SPT.IntA)): pass
class IaIb(static_proxy(None, SPT.IntA, SPT.IntB)): pass
class CaIa(static_proxy(SPT.ClassA, SPT.IntA)): pass
class CaIaIb(static_proxy(SPT.ClassA, SPT.IntA, SPT.IntB)): pass


class ProtectedChild(static_proxy(SPT.ProtectedParent)):
    @method(jvoid, [String])
    def setViaChildMethod(self, s):
        self.setViaParent(s)

    @method(jvoid, [String])
    def setViaChildField(self, s):
        self.s = s

    @method(String, [])
    def getViaChildField(self):
        return self.s


class OverloadedMethod(static_proxy()):
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


class Return(static_proxy()):
    @method(jvoid, [])
    def void_good(self):            pass

    @method(jvoid, [])
    def void_bad(self):             return "hello"

    @method(jint, [])
    def primitive_good(self):       return 42

    @method(jint, [])
    def primitive_bad_value(self):  return "hello"

    @method(jint, [])
    def primitive_bad_null(self):   pass

    @method(String, [])
    def object_good_value(self):    return "hello"

    @method(String, [])
    def object_good_null(self):     return None

    @method(String, [])
    def object_bad(self):           return 42

    @method(jarray(String), [])
    def array_good_value(self):     return ["hello", "world"]

    @method(jarray(String), [])
    def array_good_null(self):      return None

    @method(jarray(String), [])
    def array_bad_content(self):    return [1, 2]

    @method(jarray(String), [])
    def array_bad_value(self):      return "hello"
