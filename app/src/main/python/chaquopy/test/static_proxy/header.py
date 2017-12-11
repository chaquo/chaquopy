from __future__ import absolute_import, division, print_function

from java import method, static_proxy
from java.lang import String
from com.chaquo.java import StaticProxyTest as SPT


class OtherPackage(static_proxy(package="other.pkg")):
    @method(String, [])
    def hello(self):
        return "world"


class Ca(static_proxy(SPT.ClassA)):
    pass
class Ia(static_proxy(None, SPT.IntA)):
    pass
class IaIb(static_proxy(None, SPT.IntA, SPT.IntB)):
    pass
class CaIa(static_proxy(SPT.ClassA, SPT.IntA)):
    pass
class CaIaIb(static_proxy(SPT.ClassA, SPT.IntA, SPT.IntB)):
    pass
