from java import *


class C(static_proxy(None)):
    @method(jvoid, jint)
    def f(*args):
        pass
