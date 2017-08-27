from java import *

from com.example import Class1, Class2


class Simple(static_proxy(None)):
    @constructor([])
    def __init__(*args):
        pass


# args, throws and modifiers are fully covered by test_method.
class Overload(static_proxy(None)):
    @constructor([])
    @constructor([Class1], modifiers="protected", throws=[Class2])
    def __init__(*args):
        pass
