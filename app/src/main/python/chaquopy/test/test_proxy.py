from __future__ import absolute_import, division, print_function

from java import cast, dynamic_proxy, jarray, jfloat, jint
import traceback

from .test_utils import FilterWarningsCase
from com.chaquo.python import PyException, TestProxy as TP


class TestProxy(FilterWarningsCase):
    from .test_utils import assertDir

    def test_direct_inherit(self):
        from java.lang import Object, Runnable
        for base in [Object, Runnable]:
            with self.assertRaisesRegexp(TypeError, "Java classes can only be inherited using "
                                         "static_proxy or dynamic_proxy"):
                class P(base):
                    pass

    def test_dynamic_errors(self):
        from java.lang import Object, Runnable
        with self.assertRaisesRegexp(TypeError, "'hello' is not a Java interface"):
            class P1(dynamic_proxy("hello")):
                pass
        with self.assertRaisesRegexp(TypeError,
                                     "<class 'java.lang.Object'> is not a Java interface"):
            class P2(dynamic_proxy(Object)):
                pass
        with self.assertRaisesRegexp(TypeError, "<class 'chaquopy.test.test_proxy.P3'> "
                                     "is not a Java interface"):
            class P3(dynamic_proxy(Runnable)):
                pass
            class P4(dynamic_proxy(P3)):
                pass

        with self.assertRaisesRegexp(TypeError, "dynamic_proxy must be used first in class bases"):
            class B(object):
                pass
            class P5(B, dynamic_proxy(Runnable)):
                pass
        with self.assertRaisesRegexp(TypeError,
                                     "dynamic_proxy can only be used once in class bases"):
            class P6(dynamic_proxy(Runnable), dynamic_proxy(Runnable)):
                pass

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

        from .test_utils import Object_names
        Proxy_names = Object_names | {"getInvocationHandler", "getProxyClass", "isProxyClass",
                                      "newProxyInstance",
                                      "h"}              # reflect.Proxy instance field
        Adder_names = Object_names | {"constant", "add"}
        AddN_names = Proxy_names | Adder_names
        self.assertDir(TP.Adder, Adder_names)
        self.assertDir(AddN, AddN_names)

        AddN_instance_names = AddN_names | {"n"}        # Python instance field
        self.assertDir(a2, AddN_instance_names)
        a2.foo = 42
        self.assertDir(a2, AddN_instance_names | {"foo"})

    def test_multiple(self):
        # These both implement the same interfaces, and will therefore be represented by the
        # same Java class. Make sure they retain their Python types after a round trip through
        # Java.
        class Add1(dynamic_proxy(TP.Adder)):
            def add(self, x):
                return x + 1
        class Add2(dynamic_proxy(TP.Adder)):
            def add(self, x):
                return x + 2

        TP.a1 = Add1()
        TP.a2 = Add2()
        self.assertEqual(11, TP.a1.add(10))
        self.assertEqual(12, TP.a2.add(10))

    def test_gc(self):
        from .pyobjecttest import DelTrigger as DT

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

        DT.reset()
        a = A(5)
        DT.assertTriggered(self, False)
        TP.a1 = a
        a = None
        DT.assertTriggered(self, False)
        a = TP.a1
        self.assertIsInstance(a, A)
        self.assertEqual(5, a.before_init_n)
        self.assertEqual(-5, a.after_init_n)
        self.assertEqual(7, cast(TP.Adder, a).add(2))

        a_Adder = cast(TP.Adder, a)
        self.assertNotIsInstance(a_Adder, A)
        self.assertFalse(hasattr(a_Adder, "before_init_n"))
        a = None
        DT.assertTriggered(self, False)
        a = cast(A, a_Adder)
        self.assertIsInstance(a, A)
        self.assertEqual(5, a.before_init_n)
        a_Adder = None

        TP.a1 = None
        DT.assertTriggered(self, False)
        a = None
        DT.assertTriggered(self, True)

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
            TP.a1 = a
        with error:
            a.toString()
        with error:
            cast(TP.Adder, a)

        super(A, a).__init__()
        TP.a1 = a
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
        with self.assertRaisesRegexp(PyException, r"TestProxy\$Adder.add is abstract"):
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
                return "Override " + Object.toString(self)
            def hashCode(self):
                return Object.hashCode(self) + 1
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

    def test_object_methods_final(self):
        from java.lang import IllegalMonitorStateException
        class C(dynamic_proxy(TP.Adder)):
            def wait(self):
                return "Python override"

        c = C()
        self.assertEqual("Python override", c.wait())
        with self.assertRaises(IllegalMonitorStateException):
            cast(TP.Adder, c).wait()

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
        class C(dynamic_proxy(Runnable, TP.Adder, TP.GetString)):
            def run(self):
                return self.result  # returns void
            def add(self, x):
                return self.result  # returns int
            def getString(self):
                return self.result  # returns String

        c = C()
        c_Runnable, c_Adder, c_GS = [cast(cls, c) for cls in [Runnable, TP.Adder, TP.GetString]]
        c.result = None
        self.assertIsNone(c_Runnable.run())
        with self.assertRaises(NullPointerException):
            c_Adder.add(42)
        self.assertIsNone(c_GS.getString())

        c.result = 42
        with self.assertRaisesRegexp(ClassCastException, "Cannot convert int object to void"):
            c_Runnable.run()
        self.assertEqual(42, c_Adder.add(99))
        with self.assertRaisesRegexp(ClassCastException, "Cannot convert int object to "
                                     "java.lang.String"):
            c_GS.getString()

        c.result = "hello"
        with self.assertRaisesRegexp(ClassCastException, "Cannot convert str object to void"):
            c_Runnable.run()
        with self.assertRaisesRegexp(ClassCastException, "Cannot convert str object to "
                                     "java.lang.Integer"):
            c_Adder.add(99)
        self.assertEqual("hello", c_GS.getString())

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

        with self.assertRaisesRegexp(PyException, args_error(1, 2)):
            c_Args.tooMany(42)
        with self.assertRaisesRegexp(PyException, args_error(2, 1)):
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

        with self.assertRaisesRegexp(TypeError, args_error(1, 0, varargs=True)):
            c_Args.varargs()
        self.assertEqual("", c_Args.varargs(":"))
        self.assertEqual("hello", c_Args.varargs("|", "hello"))
        self.assertEqual("hello|world", c_Args.varargs("|", "hello", "world"))

    def test_exception(self):
        from java.io import FileNotFoundException, EOFException
        from java.lang import RuntimeException
        from java.lang.reflect import UndeclaredThrowableException
        from com.chaquo.python import PyException

        ref_line_no = traceback.extract_stack()[-1][1]  # Line number of THIS line.
        class E(dynamic_proxy(TP.Exceptions)):
            def fnf(self):
                raise E.exc_cls("fnf")
        e_cast = cast(TP.Exceptions, E())

        fnf_frames = [
            ("<python>.chaquopy.test.test_proxy", "fnf", "test_proxy.py", ref_line_no + 3),
            ("com.chaquo.python.PyObject", "callAttrThrows", None, None),
            ("com.chaquo.python.PyInvocationHandler", "invoke", "PyInvocationHandler.java", None)]

        def assertFnfThrows(message, throw_cls, catch_cls=None, check_cause=False):
            if catch_cls is None:
                catch_cls = throw_cls
            E.exc_cls = throw_cls
            try:
                e_cast.fnf()
            except catch_cls as e:
                check_e = e.getCause() if check_cause else e
                self.assertEqual(message, check_e.getMessage())
                self.assertHasFrames(check_e, fnf_frames)
            else:
                self.fail()

        assertFnfThrows("fnf", FileNotFoundException)               # Declared checked exception
        assertFnfThrows("fnf", EOFException,                        # Undeclared checked exception
                        UndeclaredThrowableException,
                        check_cause=True)
        assertFnfThrows("fnf", RuntimeException)                    # Unchecked exception
        assertFnfThrows("TypeError: fnf", TypeError, PyException)   # Python exception

    def test_exception_indirect(self):
        from java.lang import Integer, NumberFormatException

        ref_line = traceback.extract_stack()[-1][1]  # Line number of THIS line.
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
            self.assertHasFrames(e, [
                ("java.lang.Integer", "parseInt", None, None),
                ("<python>.chaquopy.test.test_proxy", "indirect_parse", "test_proxy.py",
                 ref_line + 5),
                ("<python>.chaquopy.test.test_proxy", "parse", "test_proxy.py", ref_line + 3),
                ("com.chaquo.python.PyObject", "callAttrThrows", None, None)])
        else:
            self.fail()

    def test_exception_in_init(self):
        from java.lang import Runnable
        ref_line_no = traceback.extract_stack()[-1][1]  # Line number of THIS line.
        class C(dynamic_proxy(Runnable)):
            def run(self):
                from . import exception_in_init  # noqa: F401

        c = C()
        try:
            cast(Runnable, c).run()
        except PyException as e:
            self.assertEqual("ValueError: Exception in __init__.py", e.getMessage())
            self.assertHasFrames(e, [
                ("<python>.chaquopy.test.exception_in_init", "<module>", "__init__.py", 3),
                ("<python>.java.chaquopy", "import_override", "import.pxi", None),
                ("<python>.chaquopy.test.test_proxy", "run", "test_proxy.py", ref_line_no + 3),
                ("com.chaquo.python.PyObject", "callAttrThrows", None, None)])

    # Checks that the given Java exception has the given frames in the given order (ignoring
    # any other frames before, between and after).
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
        raise AssertionError("{} not found in {}".format(frames[i_frame], e.getStackTrace()))

    # Test a non-Chaquopy proxy class, implemented in Java in the conventional way.
    def test_java_implemented(self):
        p = TP.newProxy()

        TP.javaRun = False
        p.run()
        self.assertEqual(True, TP.javaRun)

        self.assertEqual("tf", p.tooFew())
        self.assertEqual(5, p.addDuck(2, 2))
        self.assertEqual(4.5, p.addDuck(2, 1.5))
        self.assertEqual("helloworldX", p.addDuck("hello", "world"))

        from java.lang import RuntimeException
        with self.assertRaisesRegexp(RuntimeException, "Not implemented: tooMany"):
            p.tooMany(42)


def args_error(expected, given, varargs=False):
    py2_error = (r"takes {} arguments? \({} given\)"
                 .format(("no" if expected == 0 else
                          "at least {}".format(expected) if varargs else
                          "exactly {}".format(expected)),
                         given))
    if given < expected:
        py3_error = r"missing {} required positional arguments?".format(expected - given)
    else:
        py3_error = (r"takes {} positional arguments? but {} (were|was) given"
                     .format(expected, given))
    return r"{}|{}".format(py2_error, py3_error)
