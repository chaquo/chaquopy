from java import *
from com.example import ClassA, IntA, IntB


class NoBases(static_proxy(None)):
    pass

class Ca(static_proxy(ClassA)):
    pass

class Ia(static_proxy(None, IntA)):
    pass

class IaIb(static_proxy(None, IntA, IntB)):
    pass

class IbIa(static_proxy(None, IntB, IntA)):
    pass

class CaIa(static_proxy(ClassA, IntA)):
    pass

class CaIaIb(static_proxy(ClassA, IntA, IntB)):
    pass
