# FIXME:
#
# Python bases
# Python constructor
#   Test access Java members before calling superclass init
# Python state persistence
#
# Mismatching override (Python signature doesn't accept java signature)
# Python returns object of wrong type

# Void return (See definition == 'V' in p2j)
# Overloaded override
# Varargs override (should receive jarray)
# *args override (should receive list)
# Generic parameters and return
# Generic interface
#
# Multiple interfaces
# Can access Java members but cannot overwrite or hide them
#
# Thrown exceptions
#
# Unimplemented method (may require nonvirtual change: if so, commit first)
#
# toString, hashCode and equals called from Java should delegate to Python methods of same name
#   if present, otherwise Object. Python special methods continue to invoke Java method name,
#   which will go directly to the Python implementation if present.
#
# Implicit callable conversion to functional interface

from __future__ import absolute_import, division, print_function

from unittest import TestCase

from java import *
from java.lang import ClassCastException
from com.chaquo.python import PyException, TestProxy as TP


class TestProxy(TestCase):

    def test_direct_inherit(self):
        from java.lang import Object, Runnable
        for base in [Object, Runnable]:
            with self.assertRaisesRegexp(TypeError, "Java classes can only be inherited using "
                                         "static_proxy or dynamic_proxy"):
                class P(base): pass

    def test_dynamic_errors(self):
        from java.lang import Object, Runnable
        with self.assertRaisesRegexp(TypeError, "'hello' is not a Java interface"):
            class P(dynamic_proxy("hello")): pass
        with self.assertRaisesRegexp(TypeError, "<class 'java.lang.Object'> is not a Java interface"):
            class P(dynamic_proxy(Object)): pass
        with self.assertRaisesRegexp(TypeError, "<class 'test_proxy.P'> is not a Java interface"):
            class P(dynamic_proxy(Runnable)): pass
            class P2(dynamic_proxy(P)): pass

        with self.assertRaisesRegexp(TypeError, "dynamic_proxy must be used first in class bases"):
            class B(object): pass
            class C(B, dynamic_proxy(Runnable)): pass
        with self.assertRaisesRegexp(TypeError, "dynamic_proxy can only be used once in class bases"):
            class C(dynamic_proxy(Runnable), dynamic_proxy(Runnable)): pass

    def test_void(self):
        from java.lang import Runnable
        class Runner(dynamic_proxy(Runnable)):
            def __init__(self, result, do_return):
                super(Runner, self).__init__()
                self.result = result
                self.do_return = do_return
            def run(self):
                TP.runResult = self.result
                if self.do_return:
                    return self.result

        self.assertEqual("hello", TP.run(Runner("hello", False)))

        with self.assertRaisesRegexp(ClassCastException, "Cannot convert str object to void"):
            TP.run(Runner("hello", True))

    def test_basic(self):
        class Add1(dynamic_proxy(TP.Adder)):
            def add(self, x):
                return x + 1

        a1 = Add1()
        self.assertEqual(2, TP.add(a1, 1))
        self.assertEqual(2, a1.add(1))

    def test_python_state(self):
        class AddN(dynamic_proxy(TP.Adder)):
            def __init__(self, n):
                super(AddN, self).__init__()
                self.n = n
            def add(self, x):
                return self.n + x

        a2, a3 = AddN(2), AddN(3)
        self.assertEqual(5, TP.add(a2, 3))
        self.assertEqual(6, TP.add(a3, 3))

        TP.adder = a2
        del a2
        a2 = TP.adder
        self.assertEqual(5, TP.add(a2, 3))

    def test_object_methods(self):
        class AnAdder(dynamic_proxy(TP.Adder)):
            def toString(self):
                return "anadder"

        a1 = AnAdder()
        self.assertEqual("anadder", TP.toString(a1))
        # FIXME test equals and hashCode, and test unimplemented
