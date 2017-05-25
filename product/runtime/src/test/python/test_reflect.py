from __future__ import absolute_import, division, print_function
import unittest
from java import *


class ReflectTest(unittest.TestCase):

    def setUp(self):
        self.Test = jclass('com.chaquo.python.TestBasics')
        self.t = self.Test()

    def test_bootstrap(self):
        # Test a non-inherited method which we are unlikely ever to use in the reflection
        # process.
        klass = jclass("java.lang.Class").forName("java.lang.String")
        self.assertIsInstance(klass.desiredAssertionStatus(), bool)

    def test_jclass(self):
        Stack = jclass('java.util.Stack')
        StackSlash = jclass('java/util/Stack')
        self.assertIs(Stack, StackSlash)
        stack = Stack()
        self.assertIsInstance(stack, Stack)

        with self.assertRaisesRegexp(JavaException, "NoClassDefFoundError: java/lang/Stakk"):
            jclass("java.lang.Stakk")

    # Most of the positive tests are in test_conversion, but here are some error tests.
    def test_static(self):
        for obj in [self.Test, self.t]:
            no_attr_msg = ("' object has no attribute" if obj is self.t
                           else "type object '.+' has no attribute")
            with self.assertRaisesRegexp(AttributeError, no_attr_msg):
                obj.staticNonexistent
            with self.assertRaisesRegexp(AttributeError, no_attr_msg):
                obj.staticNonexistent = True
            with self.assertRaisesRegexp(AttributeError, "final"):
                obj.fieldStaticFinalZ = True
            with self.assertRaisesRegexp(AttributeError, "not a field"):
                obj.setStaticZ = True
            with self.assertRaisesRegexp(TypeError, "not callable"):
                obj.fieldStaticZ()
            with self.assertRaisesRegexp(TypeError, "takes 0 arguments"):
                obj.staticNoArgs(True)
            with self.assertRaisesRegexp(TypeError, "takes 1 argument"):
                obj.setStaticZ()

    # Most of the positive tests are in test_conversion, but here are some error tests.
    def test_instance(self):
        with self.assertRaisesRegexp(AttributeError, "object has no attribute"):
            self.t.nonexistent
        with self.assertRaisesRegexp(AttributeError, "object has no attribute"):
            self.t.nonexistent = True
        with self.assertRaisesRegexp(AttributeError, "final"):
            self.t.fieldFinalZ = True
        with self.assertRaisesRegexp(AttributeError, "not a field"):
            self.t.setZ = True
        with self.assertRaisesRegexp(TypeError, "not callable"):
            self.t.fieldZ()
        with self.assertRaisesRegexp(TypeError, "takes 0 arguments"):
            self.t.noArgs(True)
        with self.assertRaisesRegexp(TypeError, "takes 1 argument"):
            self.t.setZ()

        with self.assertRaisesRegexp(AttributeError, "static context"):
            self.Test.fieldZ
        with self.assertRaisesRegexp(AttributeError, "static context"):
            self.Test.fieldZ = True
        with self.assertRaisesRegexp(AttributeError, "static context"):
            self.Test.getZ()

    # This might seem silly, but an older version had a bug where bound methods could be
    # rebound by getting the same method from a different object, or instantiating a new object
    # of the same class.
    def test_multiple_instances(self):
        test1, test2 = self.Test(), self.Test()
        test1.fieldB = 127
        test2.fieldB = 10

        self.assertEquals(test2.fieldB, 10)
        self.assertEquals(test1.fieldB, 127)
        self.assertEquals(test2.fieldB, 10)
        self.assertEquals(test2.getB(), 10)
        self.assertEquals(test1.getB(), 127)
        self.assertEquals(test2.getB(), 10)

        method1 = test1.getB
        method2 = test2.getB
        self.assertEquals(method1(), 127)
        self.assertEquals(method2(), 10)
        self.assertEquals(method1(), 127)
        test3 = self.Test()
        test3.fieldB = 42
        self.assertEquals(method1(), 127)
        self.assertEquals(method2(), 10)

        test1.fieldB = 11
        test2.fieldB = 22
        self.assertEquals(test1.fieldB, 11)
        self.assertEquals(test2.fieldB, 22)
        self.assertEquals(test1.getB(), 11)
        self.assertEquals(test2.getB(), 22)

    def test_mixed_params(self):
        test = jclass('com.chaquo.python.TestBasics')()
        self.assertEquals(test.methodParamsZBCSIJFD(
            True, 127, 'k', 32767, 2147483467, 9223372036854775807, 1.23, 9.87), True)

    def test_out(self):
        # System.out implies recursive lookup and instantiation of the PrintWriter proxy class.
        System = jclass('java.lang.System')

        # TODO #5181 This should be implemented in JavaObject.__new__, using identityHashCode
        # followed by IsSameObject. Consider how this will interact with aliases created by
        # `cast`; `is` probably can't say that they're also the same object, but that's not a
        # major problem (document at `cast`). Test garbage collection just like in the Java
        # unit tests.
        #
        # self.assertIs(System.out, System.out)

        self.assertEqual(False, System.out.checkError())
        self.assertIsNone(System.out.flush())

    def test_unconstructible(self):
        System = jclass("java.lang.System")
        with self.assertRaisesRegexp(TypeError, "no accessible constructors"):
            System()

    def test_reserved_words(self):
        StringWriter = jclass("java.io.StringWriter")
        PrintWriter = jclass("java.io.PrintWriter")
        self.assertIs(PrintWriter.__dict__["print"], PrintWriter.__dict__["print_"])
        sw = StringWriter()
        pw = PrintWriter(sw)
        self.assertTrue(hasattr(pw, "print_"))
        self.assertFalse(hasattr(pw, "flush_"))
        pw.print_("Hello")
        pw.print_(" world")
        self.assertEqual("Hello world", sw.toString())
