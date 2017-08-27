from java import *

from com.example import Class1, Class2


class C(static_proxy(None)):
    @method(jvoid, [])
    def void_(*args):
        pass

    @method(jint, [])
    def integral(*args):
        pass

    @method(jfloat, [])
    def floating(*args):
        pass

    @method(jboolean, [])
    def boolean_(*args):
        pass

    @method(jchar, [])
    def char_(*args):
        pass

    @method(Class1, [])
    def class_(*args):
        pass

    @method(jarray(jint), [])
    def array(*args):
        pass
