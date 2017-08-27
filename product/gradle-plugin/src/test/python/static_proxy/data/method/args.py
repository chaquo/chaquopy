from java import *

from com.example import Class1, Class2


class Primitive(static_proxy(None)):
    @method(jvoid, [])
    def zero(*args):
        pass

    @method(jvoid, [jbyte, jshort, jint, jlong])
    def integral(*args):
        pass

    @method(jvoid, [jfloat, jdouble])
    def floating(*args):
        pass

    @method(jvoid, [jboolean, jchar])
    def other(*args):
        pass


class Class(static_proxy(None)):
    @method(jvoid, [Class1])
    def simple1(*args):
        pass

    @method(jvoid, [Class1, Class2])
    def simple2(*args):
        pass

    @method(jvoid, [Class1.Class11])
    def nested1(*args):
        pass

    @method(jvoid, [Class1.Class11.Class111])
    def nested2(*args):
        pass


class Array(static_proxy(None)):
    @method(jvoid, [jarray(jint)])
    def primitive1d(*args):
        pass

    @method(jvoid, [jarray(jarray(jint))])
    def primitive2d(*args):
        pass

    @method(jvoid, [jarray(Class1)])
    def class1d(*args):
        pass

    @method(jvoid, [jarray(jarray(Class1))])
    def class2d(*args):
        pass


class Mixed(static_proxy(None)):
    @method(jvoid, [jint, Class1, jarray(jint)])
    def mixed1(*args):
        pass
