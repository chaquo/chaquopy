from java import (static_proxy, constructor as cons,
                  method, Override as Over,
                  jvoid, jfloat as jf, jchar as jc,
                  jarray, jboolean as jb)

from com.example import Class1 as C1, Class2


class C(static_proxy(None)):
    @cons([])
    def __init__(*args):
        pass

    @method(jvoid, [], throws=[C1])
    def method1(*args):
        pass

    @Over(jf, [jb])
    @Over(jc, [jarray(jarray(Class2))])
    def method2(*args):
        pass
