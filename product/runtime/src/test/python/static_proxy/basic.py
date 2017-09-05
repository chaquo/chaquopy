# FIXME:
#
# Overloads
# Return conversions
# Exceptions
# See Google doc for more
#
# Defend against the static proxy class being reflected under its Java name before being
# created in Python. Or is that really a problem?
#
# Removed from JavaClass.__new__ because of dynamic_proxy many-to-one issue:
# if java_name in jclass_cache:
#     raise TypeError(f"Java class '{java_name}' has already been reflected")

from __future__ import absolute_import, division, print_function

from java import *

class Adder(static_proxy(None)):
    @constructor([jint])
    def __init__(self, n):
        self.n = n

    @method(jint, [jint])
    def add(self, x):
        return self.n + x


# class Foo(static_proxy(Class1, Int1, Int2, package="test")):

#     @constructor([jint, Class1], modifiers="protected", throws=[Class1, Class2])
#     @constructor([])
#     @constructor([jarray(jboolean)])
#     def __init__(*args):
#         pass

#     @method(jvoid, [jint])
#     def f(): pass

#     @method(Class2, [jint, Int2], throws=[Int1])
#     def g(): pass

#     @method(jint, [])
#     def h(): pass
