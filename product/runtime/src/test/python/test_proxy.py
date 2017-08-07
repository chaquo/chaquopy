# FIXME:
# Python bases
# Python constructor
# Python state persistence
# Varargs override (should receive jarray)
# *args override (should received list)
# Overloaded override
# Generic parameters and return
# Generic interface
# Unimplemented method inherited from Object (toString)
# Unimplemented method (may require nonvirtual change: if so, commit first)
# Thrown exceptions
# Can access Java members but cannot overwrite or hide them
# Test access Java members before calling superclass init
# Void return (See definition == 'V' in p2j)


from __future__ import absolute_import, division, print_function

from unittest import TestCase

from java import *

from com.chaquo.python import TestProxy as TP

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

    def test_basic(self):
        class Add1(dynamic_proxy(TP.Adder)):
            def add(self, x):
                return x + 1

        a1 = Add1()
        self.assertEqual(2, TP.add(a1, 1))
        self.assertEqual(2, a1.add(1))
