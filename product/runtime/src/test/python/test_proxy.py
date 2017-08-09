# FIXME:
#
# Can call Object methods and read instance constants via `self`, but cannot overwrite or hide them
#
# Unimplemented method (may require nonvirtual change: if so, commit first)
# toString, hashCode and equals called from Java should delegate to Python methods of same name
#   if present, otherwise Object. Python special methods continue to invoke Java method name,
#   which will go directly to the Python implementation if present.
#
# Thrown exceptions


from __future__ import absolute_import, division, print_function

from unittest import TestCase

from java import *
from java.lang import ClassCastException, NullPointerException
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

    def test_basic(self):
        class AddN(dynamic_proxy(TP.Adder)):
            def __init__(self, n):
                super(AddN, self).__init__()
                self.n = n
            def add(self, x):
                return self.n + x

        a2, a3 = AddN(2), AddN(3)
        self.assertEqual(5, cast(TP.Adder, a2).add(3))
        self.assertEqual(6, cast(TP.Adder, a3).add(3))

        TP.a = a2
        del a2
        a = TP.a
        self.assertIsInstance(a, AddN)
        self.assertEqual(5, cast(TP.Adder, a).add(3))

    def test_attribute_errors(self):
        class GetBeforeInit(dynamic_proxy(TP.Adder)):
            def __init__(self):
                self.n
        with self.assertRaisesRegexp(AttributeError, "dynamic_proxy superclass __init__ must be "
                                     "called before accessing attributes"):
            GetBeforeInit()

        class SetBeforeInit(dynamic_proxy(TP.Adder)):
            def __init__(self):
                self.n = 99
        with self.assertRaisesRegexp(AttributeError, "dynamic_proxy superclass __init__ must be "
                                     "called before accessing attributes"):
            SetBeforeInit()

        class GetNonexistent(dynamic_proxy(TP.Adder)):
            def add(self, x):
                self.n
        with self.assertRaisesRegexp(PyException, "'GetNonexistent' object has no attribute 'n'"):
            cast(TP.Adder, GetNonexistent()).add(5)

    def test_interface_constant(self):
        class AddConstant(dynamic_proxy(TP.Adder)):
            def add(self, x):
                return x + self.constant

        self.assertEqual(123, AddConstant.constant)
        with self.assertRaisesRegexp(AttributeError, "constant is a final field"):
            AddConstant.constant = 321

        a = AddConstant()
        self.assertEqual(125, a.add(2))
        with self.assertRaisesRegexp(AttributeError, "constant is a final field"):
            a.constant = 321

    def test_object_methods(self):
        class AnAdder(dynamic_proxy(TP.Adder)):
            def toString(self):
                return "anadder"

        a1 = AnAdder()
        self.assertEqual("anadder", TP.toString(a1))
        # FIXME test equals and hashCode, and test unimplemented
        # FIXME test cannot assign to Object methods

    def test_python_base(self):
        class B(object):
            def forty_two(self):
                return 42
        class C(dynamic_proxy(TP.Adder), B):
            def add(self, x):
                return x + self.forty_two()

        self.assertEqual(47, cast(TP.Adder, C()).add(5))

    def test_return(self):
        from java.lang import Runnable
        class C(dynamic_proxy(Runnable, TP.Adder)):
            def add(self, x):
                return self.result
            def run(self):
                return self.result

        c = C()
        c_Runnable, c_Adder = cast(Runnable, c), cast(TP.Adder, c)
        c.result = None
        c_Runnable.run()
        with self.assertRaises(NullPointerException):
            c_Adder.add(42)

        c.result = 42
        with self.assertRaisesRegexp(ClassCastException, "Cannot convert int object to void"):
            c_Runnable.run()
        self.assertEqual(42, c_Adder.add(99))

        c.result = "hello"
        with self.assertRaisesRegexp(ClassCastException,
                                     "Cannot convert str object to java.lang.Integer"):
            c_Adder.add(99)
        c.result = c
        with self.assertRaisesRegexp(ClassCastException,
                                     "Cannot convert C object to java.lang.Integer"):
            c_Adder.add(99)

    def test_args(self):
        from java.lang import String
        test = self
        class C(dynamic_proxy(TP.Args)):
            def tooMany(self):
                pass
            def tooFew(self, a):
                pass
            def addDuck(self, a, b):
                return a + b
            def star(self, *args):
                return ",".join(args)
            def varargs(self, delim, args):
                test.assertIsInstance(args, jarray(String))
                return delim.join(args)

        c = C()
        c_Args = cast(TP.Args, c)

        with self.assertRaisesRegexp(PyException, "1 argument \(2 given\)"):
            c_Args.tooMany(42)
        with self.assertRaisesRegexp(PyException, "2 arguments \(1 given\)"):
            c_Args.tooFew()

        self.assertEqual(3, c_Args.addDuck(jint(1), jint(2)))
        self.assertAlmostEqual(3.5, c_Args.addDuck(jfloat(1), jfloat(2.5)))
        self.assertEqual("helloworld", c_Args.addDuck("hello", "world"))

        self.assertEqual("", c_Args.star())
        self.assertEqual("hello", c_Args.star("hello"))
        self.assertEqual("hello,world", c_Args.star("hello", "world"))
        with self.assertRaisesRegexp(TypeError, "cannot be applied"):
            c_Args.star("hello", "world", "again")
        self.assertEqual("hello,world,again", c.star("hello", "world", "again"))

        with self.assertRaisesRegexp(TypeError, "takes at least 1 argument \(0 given\)"):
            c_Args.varargs()
        self.assertEqual("", c_Args.varargs(":"))
        self.assertEqual("hello", c_Args.varargs("|", "hello"))
        self.assertEqual("hello|world", c_Args.varargs("|", "hello", "world"))
