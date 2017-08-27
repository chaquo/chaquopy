from java import (static_proxy as sp, constructor as cons,
                  method as meth, Override as Over,
                  jvoid as jv, jfloat as jf, jchar as jc,
                  jarray as ja, jboolean as jb)

from com.example import Class1 as C1, Class2 as C2


class C(sp(None)):
    @cons([])
    def __init__(*args):
        pass

    @meth(jv, [], throws=[C1])
    def method1(*args):
        pass

    @Over(jf, [jb])
    @Over(jc, [ja(ja(C2))])
    def method2(*args):
        pass
