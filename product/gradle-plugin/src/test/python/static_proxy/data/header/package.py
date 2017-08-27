from java import *
from com.example import ClassA

class Default(static_proxy(ClassA)):
    pass

class Empty(static_proxy(ClassA, package="")):
    pass

class Level1(static_proxy(ClassA, package="one")):
    pass

class Level2(static_proxy(ClassA, package="one.two")):
    pass
