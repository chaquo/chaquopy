# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import sys

from java import cast, jarray, jclass

from .test_utils import FilterWarningsCase
from com.chaquo.python import TestReflect as TR


class TestReflect(FilterWarningsCase):
    from .test_utils import assertDir

    def setUp(self):
        super(TestReflect, self).setUp()
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
        StackL = jclass('Ljava/util/Stack;')
        self.assertIs(Stack, StackL)

        stack = Stack()
        self.assertIsInstance(stack, Stack)

        with self.assertRaises(jclass("java.lang.NoClassDefFoundError")):
            jclass("java.lang.Nonexistent")

    def test_cast(self):
        from java.lang import Boolean, Object
        b = Boolean(True)
        b_Object = cast(Object, b)
        self.assertIsNot(b, b_Object)
        self.assertEqual(b, b_Object)
        self.assertIs(Boolean.getClass(), b.getClass())
        self.assertIs(Boolean.getClass(), b_Object.getClass())
        self.assertIsNot(Object.getClass(), b_Object.getClass())
        self.assertIs(b_Object, cast(Object, b))
        self.assertIs(b, cast(Boolean, b_Object))

        with self.assertRaisesRegexp(TypeError, "cannot create java.lang.Boolean proxy from "
                                     "java.lang.Object instance"):
            cast(Boolean, Object())

    # Interaction of identity and casts is tested in TestReflect.test_cast and
    # TestArray.test_cast.
    def test_identity(self):
        from java.lang import Object, String
        Object_klass, String_klass = Object.getClass(), String.getClass()
        self.assertIsNot(Object_klass, String_klass)
        self.t.fieldKlass = Object_klass
        self.assertIs(Object_klass, self.t.fieldKlass)
        self.t.setKlass(String_klass)
        self.assertIs(String_klass, self.t.getKlass())

        a1, a2 = [jarray(String)(x) for x in [["one", "two"], ["three", "four"]]]
        self.assertIsNot(a1, a2)
        self.t.fieldStringArray = a1
        self.assertIs(a1, self.t.fieldStringArray)
        self.t.setStringArray(a2)
        self.assertIs(a2, self.t.getStringArray())

    def test_gc(self):
        DelTrigger = jclass("com.chaquo.python.TestReflect$DelTrigger")
        DelTrigger.reset()
        dt = DelTrigger()
        DelTrigger.assertTriggered(False)
        del dt
        DelTrigger.assertTriggered(True)

    def test_str_repr(self):
        Object = jclass('java.lang.Object')
        String = jclass('java.lang.String')

        o = Object()
        object_str = str(o)
        self.assertRegexpMatches(object_str, "^java.lang.Object@")
        self.assertEqual("<" + object_str + ">", repr(o))

        str_u = u"abc olé 中文"
        repr_u = u"<java.lang.String '{}'>".format(str_u)
        s = String(str_u)
        if sys.version_info[0] < 3:
            self.assertEqual(str_u.encode("utf-8"), str(s))
            self.assertEqual(str_u, unicode(s))  # noqa: F821
            self.assertEqual(repr_u.encode("utf-8"), repr(s))
        else:
            self.assertEqual(str_u, str(s))
            self.assertEqual(repr_u, repr(s))

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
        # Unlike Java instance objects, Java class objects are persistent, so there's no reason
        # to prevent setting new attributes on them. This also makes them consistent with
        # static and dynamic proxy class object.
        with self.assertRaisesRegexp(AttributeError, "has no attribute"):
            self.Test.staticNonexistent
        self.Test.staticNonexistent = "hello"
        self.assertEqual("hello", self.Test.staticNonexistent)
        del self.Test.staticNonexistent
        self.assertFalse(hasattr(self.Test, "staticNonexistent"))

        for obj in [self.Test, self.t]:
            with self.assertRaisesRegexp(AttributeError, "final"):
                obj.fieldStaticFinalZ = True
            with self.assertRaisesRegexp(AttributeError, "not a field"):
                obj.setStaticZ = True
            with self.assertRaisesRegexp(TypeError, "not callable"):
                obj.fieldStaticZ()
            with self.assertRaisesRegexp(TypeError, r"takes 0 arguments \(1 given\)"):
                obj.staticNoArgs(True)
            with self.assertRaisesRegexp(TypeError, r"takes at least 1 argument \(0 given\)"):
                obj.staticVarargs1()
            with self.assertRaisesRegexp(TypeError, r"takes 1 argument \(0 given\)"):
                obj.setStaticZ()

    # Most of the positive tests are in test_conversion, but here are some error tests.
    def test_instance(self):
        with self.assertRaisesRegexp(AttributeError, "has no attribute"):
            self.t.nonexistent
        with self.assertRaisesRegexp(AttributeError, "has no attribute"):
            self.t.nonexistent = True
        with self.assertRaisesRegexp(AttributeError, "final"):
            self.t.fieldFinalZ = True
        with self.assertRaisesRegexp(AttributeError, "not a field"):
            self.t.setZ = True
        with self.assertRaisesRegexp(TypeError, "not callable"):
            self.t.fieldZ()
        with self.assertRaisesRegexp(TypeError, r"takes 0 arguments \(1 given\)"):
            self.t.noArgs(True)
        with self.assertRaisesRegexp(TypeError, r"takes at least 1 argument \(0 given\)"):
            self.t.varargs1()
        with self.assertRaisesRegexp(TypeError, r"takes at least 1 argument \(0 given\)"):
            self.Test.varargs1(self.t)
        with self.assertRaisesRegexp(TypeError, r"takes 1 argument \(0 given\)"):
            self.t.setZ()

        Object = jclass("java.lang.Object")
        with self.assertRaisesRegexp(AttributeError, "static context"):
            self.Test.fieldZ
        with self.assertRaisesRegexp(AttributeError, "static context"):
            self.Test.fieldZ = True
        with self.assertRaisesRegexp(TypeError, "must be called with .*TestBasics instance "
                                     r"as first argument \(got nothing instead\)"):
            self.Test.getZ()
        with self.assertRaisesRegexp(TypeError, "must be called with .*TestBasics instance "
                                     r"as first argument \(got Object instance instead\)"):
            self.Test.getZ(Object())
        self.assertEqual(False, self.Test.getZ(self.t))

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
        PrintWriter.print   # Ensure __dict__ is populated
        PrintWriter.print_  #
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
        with self.assertRaisesRegexp(TypeError, "Interface is abstract and cannot be instantiated"):
            TR.Interface()

        self.assertEqual("Interface constant", TR.Interface.iConstant)
        with self.assertRaisesRegexp(AttributeError, "final"):
            TR.Interface.iConstant = "not constant"

        c = TR.Child()
        abstract = self.assertRaisesRegexp(NotImplementedError, "Interface.iMethod is abstract "
                                           "and cannot be called")
        with abstract:
            TR.Interface.iMethod()
        with abstract:
            TR.Interface.iMethod(c)

        # Getting an Object method directly from an interface class should return the Object
        # implementation.
        self.assertRegexpMatches(TR.Interface.toString(c),
                                 r"^com.chaquo.python.TestReflect\$Child@")

        # But calling an Object method through an interface cast should be done virtually.
        self.assertEqual("Child object", cast(TR.Interface, c).toString())

    def test_inheritance(self):
        Object = jclass("java.lang.Object")
        Interface = jclass("com.chaquo.python.TestReflect$Interface")
        SubInterface = jclass("com.chaquo.python.TestReflect$SubInterface")
        Parent = jclass("com.chaquo.python.TestReflect$Parent")
        Child = jclass("com.chaquo.python.TestReflect$Child")

        self.assertEqual((object,), Object.__bases__)
        self.assertEqual((Object,), Interface.__bases__)
        self.assertEqual((Interface,), SubInterface.__bases__)
        self.assertEqual((Object,), Parent.__bases__)
        self.assertEqual((Parent, Interface), Child.__bases__)

        from .test_utils import Object_names
        Interface_names = Object_names | {"iConstant", "iMethod"}
        Parent_names = Object_names | {"pStaticField", "pField", "pStaticMethod", "pMethod",
                                       "oStaticField", "oField", "oStaticMethod", "oMethod"}
        Child_names = Parent_names | Interface_names

        self.assertDir(Object, Object_names)
        self.assertDir(Interface, Interface_names)
        self.assertDir(Parent, Parent_names)
        self.assertDir(Child, Child_names)

        self.assertEqual("Interface constant", Child.iConstant)
        self.verify_field(Child, "pStaticField", "Parent static field")
        self.assertEqual("Parent static method", Child.pStaticMethod())
        self.verify_field(Child, "oStaticField", "Overridden static field")
        self.assertEqual("Overridden static method", Child.oStaticMethod())

        c = Child()
        self.assertTrue(isinstance(c, Child))
        self.assertTrue(isinstance(c, Parent))
        self.assertTrue(isinstance(c, Interface))
        self.assertTrue(isinstance(c, Object))
        self.assertDir(c, Child_names)
        self.assertEqual("Interface constant", c.iConstant)
        self.assertEqual("Implemented method", c.iMethod())
        self.verify_field(c, "pStaticField", "Parent static field")
        self.verify_field(c, "pField", "Parent field")
        self.assertEqual("Parent static method", c.pStaticMethod())
        self.assertEqual("Parent method", c.pMethod())
        self.verify_field(c, "oStaticField", "Overridden static field")
        self.verify_field(c, "oField", "Overridden field")
        self.assertEqual("Overridden static method", c.oStaticMethod())
        self.assertEqual("Overridden method", c.oMethod())

        c_Interface = cast(Interface, c)
        self.assertFalse(isinstance(c_Interface, Child))
        self.assertFalse(isinstance(c_Interface, Parent))
        self.assertTrue(isinstance(c_Interface, Interface))
        self.assertTrue(isinstance(c_Interface, Object))
        self.assertDir(c_Interface, Interface_names)
        self.assertEqual("Interface constant", c_Interface.iConstant)
        self.assertEqual("Implemented method", c_Interface.iMethod())

        c_Parent = cast(Parent, c)
        self.assertFalse(isinstance(c_Parent, Child))
        self.assertTrue(isinstance(c_Parent, Parent))
        self.assertFalse(isinstance(c_Parent, Interface))
        self.assertTrue(isinstance(c_Parent, Object))
        self.assertDir(c_Parent, Parent_names)
        with self.assertRaisesRegexp(AttributeError, "has no attribute"):
            c_Parent.iConstant
        with self.assertRaisesRegexp(AttributeError, "has no attribute"):
            c_Parent.iMethod()
        self.verify_field(c_Parent, "pStaticField", "Parent static field")
        self.verify_field(c_Parent, "pField", "Parent field")
        self.assertEqual("Parent static method", c_Parent.pStaticMethod())
        self.assertEqual("Parent method", c_Parent.pMethod())
        self.verify_field(c_Parent, "oStaticField", "Non-overridden static field")
        self.verify_field(c_Parent, "oField", "Non-overridden field")
        self.assertEqual("Non-overridden static method", c_Parent.oStaticMethod())
        self.assertEqual("Overridden method", c_Parent.oMethod())

    def verify_field(self, obj, name, value, modify=True):
        self.assertEqual(value, getattr(obj, name))
        if modify:
            setattr(obj, name, "Modified")
            self.assertEqual("Modified", getattr(obj, name))
            setattr(obj, name, value)
            self.assertEqual(value, getattr(obj, name))

    def test_abstract(self):
        Abstract = jclass("com.chaquo.python.TestReflect$Abstract")
        with self.assertRaisesRegexp(TypeError, "abstract"):
            Abstract()

    def test_nested(self):
        TestReflect = jclass("com.chaquo.python.TestReflect")
        for cls_name in ["Interface", "Parent", "SimpleEnum", "Abstract"]:
            self.assertIs(jclass("com.chaquo.python.TestReflect$" + cls_name),
                          getattr(TestReflect, cls_name))

        self.assertTrue(issubclass(TestReflect.ParentOuter.ChildNested, TestReflect.ParentOuter))

    def test_access(self):
        a = TR.Access()
        self.assertFalse(hasattr(a, "priv"))
        # self.assertFalse(hasattr(a, "pack"))      # Appears public on Android API 23
        self.assertEqual("protected", a.prot)
        self.assertEqual("public", a.publ)

        self.assertFalse(hasattr(a, "getPriv"))
        # self.assertFalse(hasattr(a, "getPack"))   # Appears public on Android API 23
        self.assertEqual("protected", a.getProt())
        self.assertEqual("public", a.getPubl())
