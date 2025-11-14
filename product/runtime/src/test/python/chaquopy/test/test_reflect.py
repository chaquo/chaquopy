import copy
from java import cast, jarray, jclass
import pickle
from unittest import skipIf
from .test_utils import API_LEVEL, FilterWarningsCase

from com.chaquo.python import TestReflect as TR
from java.lang import Boolean, Object, String, System


class TestReflect(FilterWarningsCase):
    from .test_utils import assertDir

    def setUp(self):
        super().setUp()
        self.Test = jclass('com.chaquo.python.TestBasics')
        self.t = self.Test()

    def nested_cls(self, name):
        return jclass("com.chaquo.python.TestReflect$" + name)

    def test_bootstrap(self):
        # Test a non-inherited method which we are unlikely ever to use in the reflection
        # process.
        klass = jclass("java.lang.Class").forName("java.lang.String")
        self.assertIsInstance(klass.desiredAssertionStatus(), bool)

    def test_jclass(self):
        self.assertEqual("java.lang", Object.__module__)
        self.assertEqual("Object", Object.__name__)
        self.assertEqual(Object.__name__, Object.__qualname__)

        Stack = jclass('java.util.Stack')
        StackSlash = jclass('java/util/Stack')
        self.assertIs(Stack, StackSlash)
        StackL = jclass('Ljava/util/Stack;')
        self.assertIs(Stack, StackL)
        self.assertEqual("java.util", Stack.__module__)
        self.assertEqual("Stack", Stack.__name__)
        self.assertEqual("Stack", Stack.__qualname__)

        stack = Stack()
        self.assertIsInstance(stack, Stack)

        with self.assertRaises(jclass("java.lang.NoClassDefFoundError")):
            jclass("java.lang.Nonexistent")

    def test_cast(self):
        b = Boolean(True)
        b_Object = cast(Object, b)
        self.assertIsNot(b, b_Object)
        self.assertEqual(b, b_Object)
        self.assertIs(Boolean.getClass(), b.getClass())
        self.assertIs(Boolean.getClass(), b_Object.getClass())
        self.assertIsNot(Object.getClass(), b_Object.getClass())
        self.assertIs(b_Object, cast(Object, b))
        self.assertIs(b, cast(Boolean, b_Object))

        for obj in [Boolean, "Ljava/lang/Boolean;"]:
            with self.subTest(obj=obj):
                with self.assertRaisesRegex(TypeError, "cannot create java.lang.Boolean "
                                            "proxy from java.lang.Object instance"):
                    cast(obj, Object())

        with self.assertRaisesRegex(jclass("java.lang.NoClassDefFoundError"),
                                    "java.lang.Nonexistent"):
            cast("Ljava/lang/Nonexistent;", Object())

        with self.assertRaisesRegex(ValueError, "Invalid JNI signature: 'java.lang.Object'"):
            cast("java.lang.Object", Object())

        for obj in [0, True, None, int, str]:
            with self.subTest(obj=obj):
                with self.assertRaisesRegex(TypeError, f"{obj!r} is not a Java type"):
                    cast(obj, Object())

    # Interaction of identity and casts is tested in TestReflect.test_cast and
    # TestArray.test_cast.
    def test_identity(self):
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

    def test_pickle(self):
        s = String("hello")
        for function in [pickle.dumps, copy.copy, copy.deepcopy]:
            with self.subTest(function=function.__name__), \
                 self.assertRaisesRegex(pickle.PicklingError, "Java objects cannot be pickled"):
                function(s)

    def test_gc(self):
        DelTrigger = self.nested_cls("DelTrigger")
        DelTrigger.reset()
        dt = DelTrigger()
        DelTrigger.assertTriggered(False)
        del dt
        DelTrigger.assertTriggered(True)

    def test_str_repr(self):
        o = Object()
        object_str = str(o)
        self.assertRegex(object_str, "^java.lang.Object@")
        self.assertEqual("<" + object_str + ">", repr(o))

        str_u = "abc olé 中文"
        repr_u = "<java.lang.String '{}'>".format(str_u)
        s = String(str_u)
        self.assertEqual(str_u, str(s))
        self.assertEqual(repr_u, repr(s))

        self.assertEqual("cast('Ljava/lang/Object;', None)", repr(cast(Object, None)))
        self.assertEqual("cast('Ljava/lang/String;', None)", repr(cast(String, None)))

    def test_eq_hash(self):
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
        with self.assertRaisesRegex(AttributeError, "has no attribute"):
            self.Test.staticNonexistent
        self.Test.staticNonexistent = "hello"
        self.assertEqual("hello", self.Test.staticNonexistent)
        del self.Test.staticNonexistent
        self.assertFalse(hasattr(self.Test, "staticNonexistent"))

        for obj in [self.Test, self.t]:
            with self.assertRaisesRegex(AttributeError, "final"):
                obj.fieldStaticFinalZ = True
            with self.assertRaisesRegex(AttributeError, "not a field"):
                obj.setStaticZ = True
            with self.assertRaisesRegex(TypeError, "not callable"):
                obj.fieldStaticZ()
            with self.assertRaisesRegex(TypeError, r"takes 0 arguments \(1 given\)"):
                obj.staticNoArgs(True)
            with self.assertRaisesRegex(TypeError, r"takes at least 1 argument \(0 given\)"):
                obj.staticVarargs1()
            with self.assertRaisesRegex(TypeError, r"takes 1 argument \(0 given\)"):
                obj.setStaticZ()

    # Most of the positive tests are in test_conversion, but here are some error tests.
    def test_instance(self):
        with self.assertRaisesRegex(AttributeError, "has no attribute"):
            self.t.nonexistent
        with self.assertRaisesRegex(AttributeError, "has no attribute"):
            self.t.nonexistent = True
        with self.assertRaisesRegex(AttributeError, "final"):
            self.t.fieldFinalZ = True
        with self.assertRaisesRegex(AttributeError, "not a field"):
            self.t.setZ = True
        with self.assertRaisesRegex(TypeError, "not callable"):
            self.t.fieldZ()
        with self.assertRaisesRegex(TypeError, r"takes 0 arguments \(1 given\)"):
            self.t.noArgs(True)
        with self.assertRaisesRegex(TypeError, r"takes at least 1 argument \(0 given\)"):
            self.t.varargs1()
        with self.assertRaisesRegex(TypeError, r"takes at least 1 argument \(0 given\)"):
            self.Test.varargs1(self.t)
        with self.assertRaisesRegex(TypeError, r"takes 1 argument \(0 given\)"):
            self.t.setZ()

        with self.assertRaisesRegex(AttributeError, "static context"):
            self.Test.fieldZ
        with self.assertRaisesRegex(AttributeError, "static context"):
            self.Test.fieldZ = True
        with self.assertRaisesRegex(TypeError, "must be called with .*TestBasics instance "
                                    r"as first argument \(got nothing instead\)"):
            self.Test.getZ()
        with self.assertRaisesRegex(TypeError, "must be called with .*TestBasics instance "
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

        self.assertEqual(test2.fieldB, 10)
        self.assertEqual(test1.fieldB, 127)
        self.assertEqual(test2.fieldB, 10)
        self.assertEqual(test2.getB(), 10)
        self.assertEqual(test1.getB(), 127)
        self.assertEqual(test2.getB(), 10)

        method1 = test1.getB
        method2 = test2.getB
        self.assertEqual(method1(), 127)
        self.assertEqual(method2(), 10)
        self.assertEqual(method1(), 127)
        test3 = self.Test()
        test3.fieldB = 42
        self.assertEqual(method1(), 127)
        self.assertEqual(method2(), 10)

        test1.fieldB = 11
        test2.fieldB = 22
        self.assertEqual(test1.fieldB, 11)
        self.assertEqual(test2.fieldB, 22)
        self.assertEqual(test1.getB(), 11)
        self.assertEqual(test2.getB(), 22)

    def test_mixed_params(self):
        test = jclass('com.chaquo.python.TestBasics')()
        self.assertEqual(test.methodParamsZBCSIJFD(
            True, 127, 'k', 32767, 2147483467, 9223372036854775807, 1.23, 9.87), True)

    def test_out(self):
        # System.out implies recursive lookup and instantiation of the PrintWriter proxy class.
        self.assertEqual(False, System.out.checkError())
        self.assertIsNone(System.out.flush())

    def test_unconstructible(self):
        with self.assertRaisesRegex(TypeError, "no accessible constructors"):
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

    # Java allows methods and fields to have the same name, because they're accessed
    # with different syntax. In this case, we always return the method.
    def test_name_clash(self):
        NameClash = self.nested_cls("NameClash")
        self.assertEqual("method", NameClash.member())
        self.assertNotEqual("field", NameClash.member)

    def test_enum(self):
        SimpleEnum = self.nested_cls("SimpleEnum")
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
        with self.assertRaisesRegex(TypeError, "Interface is abstract and cannot be instantiated"):
            TR.Interface()

        self.assertEqual("Interface constant", TR.Interface.iConstant)
        with self.assertRaisesRegex(AttributeError, "final"):
            TR.Interface.iConstant = "not constant"

        c = TR.Child()
        abstract = self.assertRaisesRegex(NotImplementedError, "Interface.iMethod is abstract "
                                          "and cannot be called")
        with abstract:
            TR.Interface.iMethod()
        with abstract:
            TR.Interface.iMethod(c)

        # Getting an Object method directly from an interface class should return the Object
        # implementation.
        self.assertRegex(TR.Interface.toString(c),
                         r"^com.chaquo.python.TestReflect\$Child@")

        # But calling an Object method through an interface cast should be done virtually.
        self.assertEqual("Child object", cast(TR.Interface, c).toString())

    def test_inheritance(self):
        Interface = self.nested_cls("Interface")
        SubInterface = self.nested_cls("SubInterface")
        Parent = self.nested_cls("Parent")
        Child = self.nested_cls("Child")

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
        with self.assertRaisesRegex(AttributeError, "has no attribute"):
            c_Parent.iConstant
        with self.assertRaisesRegex(AttributeError, "has no attribute"):
            c_Parent.iMethod()
        self.verify_field(c_Parent, "pStaticField", "Parent static field")
        self.verify_field(c_Parent, "pField", "Parent field")
        self.assertEqual("Parent static method", c_Parent.pStaticMethod())
        self.assertEqual("Parent method", c_Parent.pMethod())
        self.verify_field(c_Parent, "oStaticField", "Non-overridden static field")
        self.verify_field(c_Parent, "oField", "Non-overridden field")
        self.assertEqual("Non-overridden static method", c_Parent.oStaticMethod())
        self.assertEqual("Overridden method", c_Parent.oMethod())

    def test_inheritance_order(self):
        for name, bases in [
            ("Order_1_2", ("Interface1", "Interface2")),
            ("Order_2_1", ("Interface1", "Interface2")),
            ("Diamond", ("Order_1_2", "Order_2_1", Object)),
            ("DiamondChild", ("Parent", "Order_1_2", "Order_2_1")),

            ("Order_1_1a", ("Interface1a", "Interface1")),
            ("Order_1a_1", ("Interface1a", "Interface1")),
            ("Order_1_2_1a", ("Interface1a", "Interface1", "Interface2")),
            ("Order_1a_2_1", ("Interface1a", "Interface1", "Interface2")),

            ("Order_1a_2", ("Interface1a", "Interface2")),
            ("Order_12_1a2", ("Order_1a_2", "Order_1_2"))
        ]:
            with self.subTest(name=name):
                self.assertEqual([self.nested_cls(base) if isinstance(base, str) else base
                                  for base in bases],
                                 list(self.nested_cls(name).__bases__))

    def verify_field(self, obj, name, value, modify=True):
        self.assertEqual(value, getattr(obj, name))
        if modify:
            setattr(obj, name, "Modified")
            self.assertEqual("Modified", getattr(obj, name))
            setattr(obj, name, value)
            self.assertEqual(value, getattr(obj, name))

    def test_abstract(self):
        Abstract = self.nested_cls("Abstract")
        with self.assertRaisesRegex(TypeError, "abstract"):
            Abstract()

    def test_nested(self):
        TestReflect = jclass("com.chaquo.python.TestReflect")
        for name in ["Interface", "Parent", "SimpleEnum", "Abstract"]:
            cls = self.nested_cls(name)
            self.assertIs(cls, getattr(TestReflect, name))
            self.assertEqual("com.chaquo.python", cls.__module__)
            qualname = "TestReflect$" + name
            self.assertEqual(qualname, cls.__name__)
            self.assertEqual(qualname, cls.__qualname__)

        self.assertTrue(issubclass(TestReflect.ParentOuter.ChildNested, TestReflect.ParentOuter))

    def test_access(self):
        a = TR.Access()
        self.assertFalse(hasattr(a, "priv"))
        self.assertFalse(hasattr(a, "pack"))
        self.assertEqual("protected", a.prot)
        self.assertEqual("public", a.publ)

        self.assertFalse(hasattr(a, "getPriv"))
        self.assertFalse(hasattr(a, "getPack"))
        self.assertEqual("protected", a.getProt())
        self.assertEqual("public", a.getPubl())

    def test_call(self):
        Call = TR.Call
        self.assertEqual("anon 1", Call.anon("1"))
        self.assertEqual("lambda 2", Call.lamb("2"))
        self.assertEqual("static 3", Call.staticRef("3"))
        self.assertEqual("instance 4", Call("4").boundInstanceRef())
        self.assertEqual("instance 5", Call.unboundInstanceRef(Call("5")))
        self.assertEqual("instance 6", Call.constructorRef("6").s)

    @skipIf(not API_LEVEL, "Android only")  # TODO #1199
    def test_call_kotlin(self):
        from com.chaquo.python import TestReflectKt as TRK
        Call = TRK.Call
        self.assertEqual("kt anon 1", Call.anon("1"))
        self.assertEqual("kt lambda 2", Call.lamb("2"))
        self.assertEqual("kt func 3", Call.funcRef("3"))
        self.assertEqual("kt instance 4", Call("4").boundInstanceRef())
        self.assertEqual("kt instance 5", Call.unboundInstanceRef(Call("5")))
        self.assertEqual("kt instance 6", Call.constructorRef("6").s)

    def test_call_interface(self):
        CI = TR.CallInterface

        # No interfaces.
        with self.no_fi():
            CI.NoInterfaces()()

        # A non-functional interface.
        with self.no_fi():
            CI.NoMethods()()
        with self.no_fi():
            CI.TwoMethods()()

        # A single functional interface.
        self.assertEqual("A1.a", CI.A1()())
        self.assertEqual("Aint.a 42", CI.Aint()(42))

        # Multiple functional interfaces with the same method.
        self.assertEqual("A1A2.a", CI.A1A2()())

        # Multiple functional interfaces with different method names.
        a1b1 = CI.A1B()
        with self.multi_fi(CI.IA1, CI.IB):
            a1b1()
        self.assertEqual("A1B.a", cast(CI.IA1, a1b1)())
        self.assertEqual("A1B.b", cast(CI.IB, a1b1)())

        # Multiple functional interfaces with the same method name but different signatures.
        a1aint = CI.A1Aint()
        with self.multi_fi(CI.IA1, CI.IAint):
            a1aint()
        self.assertEqual("A1Aint.a", cast(CI.IA1, a1aint)())
        self.assertEqual("A1Aint.a 42", cast(CI.IAint, a1aint)(42))

        # Both functional and non-functional interfaces.
        self.assertEqual("A1TwoMethods.a", CI.A1TwoMethods()())

        # An abstract class which would be functional if it was an interface.
        with self.no_fi():
            CI.C()()

        # Public Object methods don't stop an interface from being functional, but protected
        # Object methods do.
        self.assertEqual("PublicObjectMethod.a", CI.PublicObjectMethod()())
        with self.no_fi():
            CI.ProtectedObjectMethod()()

        # If an interface declares one method, and a sub-interface adds a second one, then
        # the sub-interface is not functional.
        ab = CI.AB()
        self.assertEqual("AB.a", ab())
        self.assertEqual("AB.a", cast(CI.IAB, ab)())

    def test_call_interface_default(self):
        CI = TR.CallInterface
        CID = TR.CallInterfaceDefault

        # If an interface declares two methods, and a sub-interface provides a default
        # implementation for one of them, then the sub-interface is functional.
        om = CID.OneMethod()
        self.assertEqual("IOneMethod.a", om.a())
        self.assertEqual("OneMethod.b", om.b())
        self.assertEqual("OneMethod.b", om())

        # If an interface declares one method, and a sub-interface provides a default
        # implementation of it while also adding a second method, then both interfaces are
        # functional.
        abd = CID.ABDefault()
        self.assertEqual("IABDefault.a", abd.a())
        self.assertEqual("ABDefault.b", abd.b())
        with self.multi_fi(CID.IABDefault, CI.IA1):
            abd()
        self.assertEqual("IABDefault.a", cast(CI.IA1, abd)())
        self.assertEqual("ABDefault.b", cast(CID.IABDefault, abd)())

    def no_fi(self):
        return self.assertRaisesRegex(TypeError, "not callable because it implements no "
                                      "functional interfaces")

    def multi_fi(self, *interfaces):
        names_re = (", ".join(fr"{i.__module__}\.{i.__name__}" for i in interfaces)
                    .replace("$", r"\$"))
        return self.assertRaisesRegex(
            TypeError, fr"implements multiple functional interfaces \({names_re}\): "
            fr"use cast\(\) to select one")


# On Android, getDeclaredMethods and getDeclaredFields fail when the member's type refers
# to a class that cannot be loaded. Test the partial workaround in Reflector.
@skipIf(not API_LEVEL, "Android only")
class TestAndroidReflect(FilterWarningsCase):

    MEMBERS = ["tcFieldPublic", "tcFieldProtected", "tcMethodPublic", "tcMethodProtected",
               "iFieldPublic", "iFieldProtected", "iMethodPublic", "iMethodProtected",
               "finalize"]

    def test_android_reflect(self):
        from com.chaquo.python.demo import TestAndroidReflect as TAR

        if API_LEVEL >= 26:
            # TextClassifier is in the platform, so all members should be visible.
            self.assertMembers(TAR, self.MEMBERS)
        else:
            # Overridden methods should be visible, plus public methods that don't involve
            # TextClassifier.
            self.assertMembers(TAR, ["iMethodPublic", "finalize"])

    def assertMembers(self, cls, names):
        for name in names:
            with self.subTest(name=name):
                self.assertTrue(self.declares_member(cls, name))

        for name in self.MEMBERS:
            if name not in names:
                with self.subTest(name=name):
                    self.assertFalse(self.declares_member(cls, name))

    def declares_member(self, cls, name):
        hasattr(cls, name)  # Adds member to __dict__ if it exists.
        return name in cls.__dict__
