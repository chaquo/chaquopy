from java import *

from com.example import Class1, Class2


class C(static_proxy(None)):
    @method(jint, [])
    @method(Class1, [Class2])
    def method1(*args):
        pass

    @method(jvoid, [])
    @method(jboolean, [jfloat], modifiers="protected")
    @method(jchar, [jarray(Class2.Class21)], throws=[Class1])
    def method2(*args):
        pass
