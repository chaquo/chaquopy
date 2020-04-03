from java import *

from com.example import Class1, Class2


class C(static_proxy(None)):
    @method(jvoid, [])
    def default(*args):
        pass

    @method(jvoid, [], throws=None)
    def none(*args):
        pass

    @method(jvoid, [], throws=[])
    def empty(*args):
        pass

    @method(jvoid, [], throws=[Class1])
    def c1(*args):
        pass

    @method(jvoid, [], throws=[Class2])
    def c2(*args):
        pass

    @method(jvoid, [], throws=[Class1, Class2])
    def c1c2(*args):
        pass
