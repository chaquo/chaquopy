from __future__ import absolute_import, division, print_function

from java import *
from java.lang import String
from com.chaquo.java import StaticProxyTest as SPT


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
        super(OverloadedCtor, self).__init__()
        self.value = str(value)

    @method(String, [])
    def get(self):
        return self.value


class OverrideChild(static_proxy(SPT.OverrideParent)):
    @Override(String, [])
    def get(self):
        return SPT.OverrideParent.get(self) + " child"


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


from java.io import FileNotFoundException, EOFException
from java.lang import Error, RuntimeException

class Exceptions(static_proxy()):
    @method(jvoid, [])
    def undeclared_0(self):
        raise FileNotFoundException("fnf")

    @method(jvoid, [], throws=[EOFException])
    def undeclared_1(self):
        raise FileNotFoundException("fnf")

    @method(jvoid, [], throws=[EOFException])
    def declared(self):
        raise EOFException("eof")

    @method(jvoid, [])
    def python(self):
        raise TypeError("te")

    @method(jvoid, [])
    def error(self):
        raise Error("e")

    @method(jvoid, [])
    def runtime_exception(self):
        raise RuntimeException("re")


from java.lang import Thread

class Modifiers(static_proxy()):
    @method(jboolean, [], modifiers="public synchronized")
    def synced(self):
        return Thread.holdsLock(self)

    @method(jboolean, [], modifiers="public")
    def unsynced(self):
        return Thread.holdsLock(self)
