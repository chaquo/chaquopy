from __future__ import absolute_import, division, print_function

import traceback
from unittest import TestCase

from java import *
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
        self.assertEqual(2, a2.n)
        self.assertEqual(5, cast(TP.Adder, a2).add(3))  # cast() ensures the call goes through Java.
        self.assertEqual(6, cast(TP.Adder, a3).add(3))
        self.assertEqual(5, cast(TP.Adder, a2).add(3))

    # See notes in PyObjectTest.finalize_
    def test_gc(self):
        from java.lang import System
        from pyobjecttest import DelTrigger as DT

        test = self
        class A(dynamic_proxy(TP.Adder)):
            def __init__(self, n):
                self.before_init_n = n
                test.assertEqual(n, self.before_init_n)
                super(A, self).__init__()
                self.after_init_n = -n
                self.dt = DT()
            def add(self, x):
                return self.before_init_n + x

        def assertTriggered(triggered):
            System.gc()
            System.runFinalization()
            self.assertEqual(triggered, DT.triggered)

        DT.triggered = False
        a = A(5)
        assertTriggered(False)
        TP.a = a
        a = None
        assertTriggered(False)
        a = TP.a
        self.assertIsInstance(a, A)
        self.assertEqual(5, a.before_init_n)
        self.assertEqual(-5, a.after_init_n)
        self.assertEqual(7, cast(TP.Adder, a).add(2))

        a_Adder = cast(TP.Adder, a)
        self.assertNotIsInstance(a_Adder, A)
        self.assertFalse(hasattr(a_Adder, "before_init_n"))
        a = None
        assertTriggered(False)
        a = cast(A, a_Adder)
        self.assertIsInstance(a, A)
        self.assertEqual(5, a.before_init_n)
        a_Adder = None

        TP.a = None
        assertTriggered(False)
        a = None
        assertTriggered(True)

    # Using Python attributes before calling __init__ is covered by test_gc; this test covers
    # use as a Java object.
    def test_use_before_init(self):
        class A(dynamic_proxy(TP.Adder)):
            def __init__(self):
                pass

        a = A()
        error = self.assertRaisesRegexp(AttributeError, "'A' object's superclass __init__ must be "
                                        "called before using it as a Java object")
        with error:
            TP.a = a
        with error:
            a.toString()
        with error:
            cast(TP.Adder, a)

        super(A, a).__init__()
        TP.a = a
        a.toString()
        cast(TP.Adder, a)

    def test_interface_constant(self):
        class AddConstant(dynamic_proxy(TP.Adder)):
            def add(self, x):
                return x + self.constant

        a = AddConstant()
        self.assertEqual(123, a.constant)
        self.assertEqual(123, AddConstant.constant)
        self.assertEqual(125, a.add(2))
        final = self.assertRaisesRegexp(AttributeError, "constant is a final field")
        with final:
            a.constant = 321
        with final:
            AddConstant.constant = 321

    # We need a complete test of attribute behaviour because of our unusual __dict__ handling.
    def test_attribute(self):
        class AddCounter(dynamic_proxy(TP.Adder)):
            count = 0
            def add(self, x):
                result = x + AddCounter.count
                AddCounter.count += 1
                return result

        a = AddCounter()
        self.assertEqual(0, AddCounter.count)
        self.assertEqual(0, a.count)

        with self.assertRaisesRegexp(AttributeError, "'AddCounter' object has no attribute 'n'"):
            a.n

        self.assertEqual(10, a.add(10))
        self.assertEqual(21, a.add(20))
        self.assertEqual(32, a.add(30))
        self.assertEqual(3, AddCounter.count)

        a.count = 9
        self.assertEqual(9, a.count)
        self.assertEqual(43, a.add(40))
        self.assertEqual(4, AddCounter.count)
        self.assertEqual(9, a.count)

    # We need a complete test of attribute behaviour because of our unusual __dict__ handling.
    def test_descriptor(self):
        test = self
        class Add(dynamic_proxy(TP.Adder)):
            @classmethod
            def non_data(cls):
                return "classmethod"

            @property
            def data(self):
                return 42

        a = Add()
        self.assertEquals("classmethod", a.non_data())
        a.non_data = lambda: "instance override"
        self.assertEqual("instance override", a.non_data())
        del a.non_data
        self.assertEquals("classmethod", a.non_data())

        self.assertEqual(42, a.data)
        with self.assertRaisesRegexp(AttributeError, "can't set attribute"):
            a.data = 99
        with self.assertRaisesRegexp(AttributeError, "can't delete attribute"):
            del a.data

    def test_unimplemented(self):
        class A(dynamic_proxy(TP.Adder)):
            pass
        with self.assertRaisesRegexp(PyException, "TestProxy\$Adder.add is abstract"):
            cast(TP.Adder, A()).add(5)

    def test_object_methods_unimplemented(self):
        class Unimplemented(dynamic_proxy(TP.Adder)):
            pass
        a1, a2 = Unimplemented(), Unimplemented()

        ts = cast(TP.Adder, a1).toString()
        self.assertRegexpMatches(ts, r"\$Proxy.*@")
        self.assertEqual(ts, str(a1))
        self.assertNotEqual(str(a1), str(a2))

        self.assertTrue(a1.equals(a1))
        self.assertFalse(a1.equals(a2))
        self.assertTrue(a1 == a1)
        self.assertFalse(a1 == a2)
        self.assertNotEqual(a1.hashCode(), a2.hashCode())
        self.assertNotEqual(hash(a1), hash(a2))

        a1.foo = 99
        for name in ["toString", "equals", "hashCode"]:
            with self.assertRaisesRegexp(AttributeError, name + " is not a field"):
                setattr(a1, name, 99)

    def test_object_methods_implemented(self):
        from java.lang import Object
        class Implemented(dynamic_proxy(TP.Adder)):
            def toString(self):
                return "Override " + super(Implemented, self).toString()
            def hashCode(self):
                return super(Implemented, self).hashCode() + 1
            def equals(self, other):
                return True
        a1, a2 = Implemented(), Implemented()

        ts = cast(TP.Adder, a1).toString()
        self.assertRegexpMatches(ts, r"^Override .*\$Proxy.*@")
        self.assertEqual(ts, str(a1))
        self.assertNotEqual(str(a1), str(a2))

        self.assertTrue(a1.equals(a1))
        self.assertTrue(a1.equals(a2))
        self.assertEqual(Object.hashCode(a1) + 1, a1.hashCode())

    def test_python_base(self):
        class B(object):
            def forty_two(self):
                return 42
        class C(dynamic_proxy(TP.Adder), B):
            def add(self, x):
                return x + self.forty_two()

        self.assertEqual(47, cast(TP.Adder, C()).add(5))

    def test_return(self):
        from java.lang import Runnable, ClassCastException, NullPointerException
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

    def test_exception(self):
        from java.io import FileNotFoundException, EOFException
        from java.lang import RuntimeException
        from java.lang.reflect import UndeclaredThrowableException
        from com.chaquo.python import PyException

        ref_line_no = traceback.extract_stack()[-1][1]
        class E(dynamic_proxy(TP.Exceptions)):
            def fnf(self):
                raise E.exc_cls("fnf")
        e_cast = cast(TP.Exceptions, E())

        fnf_frames = [("<python>", "fnf", "test_proxy.py", ref_line_no + 3),
                      ("com.chaquo.python.PyObject", "callAttrThrows", None, None),
                      ("com.chaquo.python.PyInvocationHandler", "invoke",
                       "PyInvocationHandler.java", None)]

        def assertFnfThrows(message, throw_cls, catch_cls=None):
            if catch_cls is None:
                catch_cls = throw_cls
            E.exc_cls = throw_cls
            try:
                e_cast.fnf()
            except catch_cls as e:
                self.assertEqual(message, e.getMessage())
                self.assertHasFrames(e, fnf_frames)
            else:
                self.fail()

        assertFnfThrows("fnf", FileNotFoundException)   # Declared checked exception
        assertFnfThrows("fnf", RuntimeException)        # Undeclared unchecked exception (Java)
        assertFnfThrows("TypeError: fnf",               # Undeclared unchecked exception (Python)
                        TypeError, PyException)

        E.exc_cls = EOFException                        # Undeclared checked exception
        try:
            e_cast.fnf()
        except UndeclaredThrowableException as e:
            self.assertHasFrames(e.getCause(), fnf_frames)
        else:
            self.fail()

    def test_exception_indirect(self):
        from java.lang import Integer, NumberFormatException

        ref_line_no = traceback.extract_stack()[-1][1]
        class E(dynamic_proxy(TP.Exceptions)):
            def parse(self, s):
                return self.indirect_parse(s)
            def indirect_parse(self, s):
                return Integer.parseInt(s)
        e_cast = cast(TP.Exceptions, E())

        self.assertEqual(42, e_cast.parse("42"))
        try:
            e_cast.parse("abc")
        except NumberFormatException as e:
            self.assertHasFrames(e, [("java.lang.Integer", "parseInt", None, None),
                                     ("<python>", "indirect_parse", "test_proxy.py", ref_line_no + 5),
                                     ("<python>", "parse", "test_proxy.py", ref_line_no + 3),
                                     ("com.chaquo.python.PyObject", "callAttrThrows", None, None)])
        else:
            self.fail()

    def assertHasFrames(self, e, frames):
        i_frame = 0
        for ste in e.getStackTrace():
            cls_name, method_name, file_name, line_no = frames[i_frame]
            if ste.getClassName() == cls_name and \
               ste.getMethodName() == method_name and \
               (file_name is None or ste.getFileName() == file_name) and \
               (line_no is None or ste.getLineNumber() == line_no):
                i_frame += 1
                if i_frame == len(frames):
                    return
        raise AssertionError("{} element {} not found in {}".format(frames, i_frame,
                                                                    e.getStackTrace()))
