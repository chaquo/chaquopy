from __future__ import absolute_import, division, print_function
import unittest
from java import *


class TestReflect(unittest.TestCase):

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

        # Java SE 8 throws NoClassDefFoundError like the JNI spec says, but Android 6 throws
        # ClassNotFoundException.
        with self.assertRaisesRegexp(JavaException, "(NoClassDefFoundError|ClassNotFoundException)"):
            jclass("java.lang.Stakk")

    def test_cast(self):
        Object = jclass("java.lang.Object")
        Boolean = jclass("java.lang.Boolean")
        o = Object()
        b = Boolean(True)

        cast(Object, b)
        with self.assertRaisesRegexp(TypeError, "cannot create java.lang.Boolean proxy from java.lang.Object"):
            cast(Boolean, o)

    def test_identity(self):
        # TODO #5181
        # self.assertIs(System.out, System.out)
        pass

    # See notes in PyObjectTest.finalize_
    def test_gc(self):
        System = jclass('java.lang.System')
        DelTrigger = jclass("com.chaquo.python.TestReflect$DelTrigger")
        DelTrigger.delTriggered = False
        dt = DelTrigger()
        self.assertFalse(DelTrigger.delTriggered)
        del dt
        System.gc()
        System.runFinalization()
        self.assertTrue(DelTrigger.delTriggered)

    def test_str_repr(self):
        Object = jclass('java.lang.Object')
        String = jclass('java.lang.String')

        o = Object()
        object_str = str(o)
        self.assertRegexpMatches(object_str, "^java.lang.Object@")
        self.assertEqual("<" + object_str + ">", repr(o))

        s = String("hello")
        self.assertEqual("hello", str(s))
        self.assertEqual("<java.lang.String 'hello'>", repr(s))

        self.assertEqual("cast('Ljava/lang/Object;', None)", repr(cast(Object, None)))
        self.assertEqual("cast('Ljava/lang/String;', None)", repr(cast(String, None)))

    def test_eq_hash(self):
        String = jclass('java.lang.String')
        self.verify_equal(String("hello"), String("hello"))
        self.verify_not_equal(String("hello"), String("world"))

        LinkedList = jclass("java.util.LinkedList")
        ArrayList = jclass("java.util.ArrayList")
        Arrays = jclass("java.util.Arrays")
        l = [1, 2]
        ll = LinkedList(Arrays.asList(l))
        al = ArrayList(Arrays.asList(l))
        self.verify_equal(ll, al)
        ll.set(1, 7)
        self.verify_not_equal(ll, al)

    def verify_equal(self, a, b):
        self.assertEqual(a, b)
        self.assertEqual(b, a)
        self.assertFalse(a != b)
        self.assertFalse(b != a)
        self.assertEqual(hash(a), hash(b))

    def verify_not_equal(self, a, b):
        self.assertNotEqual(a, b)
        self.assertNotEqual(b, a)
        self.assertFalse(a == b)
        self.assertFalse(b == a)
        self.assertNotEqual(hash(a), hash(b))

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
        self.assertEqual(False, System.out.checkError())
        self.assertIsNone(System.out.flush())

    def test_unconstructible(self):
        System = jclass("java.lang.System")
        with self.assertRaisesRegexp(TypeError, "no accessible constructors"):
            System()

    def test_reserved_words(self):
        StringWriter = jclass("java.io.StringWriter")
        PrintWriter = jclass("java.io.PrintWriter")
        for name in ["print", "print_"]:  # Members are added to __dict__ on first use
            getattr(PrintWriter, name)
        self.assertIs(PrintWriter.__dict__["print"], PrintWriter.__dict__["print_"])
        sw = StringWriter()
        pw = PrintWriter(sw)
        self.assertTrue(hasattr(pw, "print_"))
        self.assertFalse(hasattr(pw, "flush_"))
        pw.print_("Hello")
        pw.print_(" world")
        self.assertEqual("Hello world", sw.toString())

    # TODO #5183
    def test_name_clash(self):
        NameClash = jclass("com.chaquo.python.TestReflect$NameClash")
        self.assertEqual("method", NameClash.member())
        self.assertNotEqual("field", NameClash.member)

    def test_enum(self):
        SimpleEnum = jclass('com.chaquo.python.TestReflect$SimpleEnum')
        self.assertTrue(SimpleEnum.GOOD)
        self.assertTrue(SimpleEnum.BAD)
        self.assertTrue(SimpleEnum.UGLY)

        self.assertEqual(SimpleEnum.GOOD, SimpleEnum.GOOD)
        self.assertNotEqual(SimpleEnum.GOOD, SimpleEnum.BAD)

        self.assertEqual(0, SimpleEnum.GOOD.ordinal())
        self.assertEqual(1, SimpleEnum.BAD.ordinal())
        self.assertEqual(SimpleEnum.values()[0], SimpleEnum.GOOD)
        self.assertEqual(SimpleEnum.values()[1], SimpleEnum.BAD)


    def test_interface(self):
        Interface = jclass("com.chaquo.python.TestReflect$Interface")
        with self.assertRaisesRegexp(TypeError, "abstract"):
            Interface()
        self.assertEqual("Interface constant", Interface.iConstant)
        with self.assertRaisesRegexp(AttributeError, "final"):
            Interface.iConstant = "not constant"
        with self.assertRaisesRegexp(AttributeError, "static context"):
            Interface.iMethod()

    def test_inheritance(self):
        Interface = jclass("com.chaquo.python.TestReflect$Interface")
        Parent = jclass("com.chaquo.python.TestReflect$Parent")
        Child = jclass("com.chaquo.python.TestReflect$Child")

        self.assertEqual("Interface constant", Child.iConstant)
        self.assertEqual("Parent static field", Child.pStaticField)
        self.assertEqual("Parent static method", Child.pStaticMethod())
        self.assertEqual("Overridden static field", Child.oStaticField)
        self.assertEqual("Overridden static method", Child.oStaticMethod())

        c = Child()
        self.assertEqual("Interface constant", c.iConstant)
        self.assertEqual("Implemented method", c.iMethod())
        self.assertEqual("Parent static field", c.pStaticField)
        self.assertEqual("Parent field", c.pField)
        self.assertEqual("Parent static method", c.pStaticMethod())
        self.assertEqual("Parent method", c.pMethod())
        self.assertEqual("Overridden static field", c.oStaticField)
        self.assertEqual("Overridden field", c.oField)
        self.assertEqual("Overridden static method", c.oStaticMethod())
        self.assertEqual("Overridden method", c.oMethod())

        c_Interface = cast(Interface, c)
        self.assertEqual("Interface constant", c_Interface.iConstant)
        self.assertEqual("Implemented method", c_Interface.iMethod())

        c_Parent = cast(Parent, c)
        self.assertEqual("Parent static field", c_Parent.pStaticField)
        self.assertEqual("Parent field", c_Parent.pField)
        self.assertEqual("Parent static method", c_Parent.pStaticMethod())
        self.assertEqual("Parent method", c_Parent.pMethod())
        self.assertEqual("Non-overridden static field", c_Parent.oStaticField)
        self.assertEqual("Non-overridden field", c_Parent.oField)
        self.assertEqual("Non-overridden static method", c_Parent.oStaticMethod())
        self.assertEqual("Overridden method", c_Parent.oMethod())

    def test_abstract(self):
        Abstract = jclass("com.chaquo.python.TestReflect$Abstract")
        with self.assertRaisesRegexp(TypeError, "abstract"):
            Abstract()
