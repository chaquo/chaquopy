from __future__ import absolute_import, division, print_function
import unittest
from java import *


class TestOverload(unittest.TestCase):

    def setUp(self):
        self.ambiguous = self.assertRaisesRegexp(TypeError, "ambiguous")
        self.inapplicable = self.assertRaisesRegexp(TypeError, "cannot be applied")

    def test_constructors(self):
        String = jclass('java.lang.String')
        self.assertEqual("", String())
        self.assertEqual("Hello World", String('Hello World'))
        with self.ambiguous:
            String(list('Hello World'))  # byte[] and char[] overloads both exist.
        self.assertEqual("Hello World", String(jarray(jchar)('Hello World')))
        self.assertEqual("lo Wo", String(jarray(jchar)('Hello World'), 3, 5))

    # Whether a call's in static or instance context should make no difference to the methods
    # considered and chosen during overload resolution.
    def test_mixed_static_and_instance(self):
        MSI = jclass("com.chaquo.python.TestOverload$MixedStaticInstance")
        m = MSI()

        self.assertEqual(m.resolve11("test"), "String")
        self.assertEqual(m.resolve11(42), "Object")

        with self.assertRaisesRegexp(TypeError, "must be called with .*MixedStaticInstance "
                                     "instance as first argument \(got str instance instead\)"):
            MSI.resolve11("test")
        self.assertEqual(MSI.resolve11(42), "Object")

        self.assertEqual(MSI.resolve11(m, "test"), "String")
        with self.inapplicable:
           MSI.resolve11(m, 42)

        # ---

        self.assertEqual(m.resolve10(), "")
        self.assertEqual(m.resolve10("test"), "String")

        with self.assertRaisesRegexp(TypeError, "must be called with .*MixedStaticInstance "
                                     "instance as first argument \(got nothing instead\)"):
            MSI.resolve10()
        self.assertEqual(MSI.resolve10("test"), "String")

        self.assertEqual(MSI.resolve10(m), "")
        with self.inapplicable:
            MSI.resolve10(m, "test")

        # ---

        self.assertEqual(m.resolve01(), "")
        self.assertEqual(m.resolve01("test"), "String")

        self.assertEqual(MSI.resolve01(), "")
        with self.assertRaisesRegexp(TypeError, "must be called with .*MixedStaticInstance "
                                     "instance as first argument \(got str instance instead\)"):
            MSI.resolve01("test")

        with self.inapplicable:
            MSI.resolve01(m)
        self.assertEqual(MSI.resolve01(m, "test"), "String")

    def test_class(self):
        Parent = jclass("com.chaquo.python.TestOverload$Parent")
        Child = jclass("com.chaquo.python.TestOverload$Child")
        Object = jclass("java.lang.Object")
        Float = jclass("java.lang.Float")
        String = jclass("java.lang.String")
        Integer = jclass("java.lang.Integer")
        s = String()
        i = Integer(42)
        f = Float(1.23)
        child = Child()
        parent = Parent()

        self.assertEqual(child.resolve(s), 'String')
        self.assertEqual(child.resolve(i), 'Integer')
        self.assertEqual(child.resolve(f), 'Object')
        self.assertEqual(child.resolve(cast(Object, s)), 'Object')
        self.assertEqual(child.resolve(cast(String, cast(Object, s))), 'String')

        with self.ambiguous:
            child.resolve(None)
        self.assertEqual(child.resolve(cast(String, None)), 'String')
        self.assertEqual(child.resolve(cast(Object, None)), 'Object')
        self.assertEqual(child.resolve(cast(String, cast(Object, None))), 'String')

        self.assertEqual(child.resolve(s, i), 'String, Object')
        self.assertEqual(child.resolve(i, s), 'Object, String')
        with self.inapplicable:
            child.resolve(i, i)

        # Casting of method parameters
        with self.ambiguous:
            child.resolve(s, s)
        self.assertEqual(child.resolve(cast(Object, s), s), 'Object, String')
        self.assertEqual(child.resolve(s, cast(Object, s)), 'String, Object')

        # Casting of object on which method is called should limit visibility of overloads.
        self.assertEqual(cast(Parent, child).resolve(s), 'Object')
        self.assertEqual(cast(Parent, child).resolve(s, s), 'Object, String')
        with self.inapplicable:
            cast(Parent, child).resolve(s, i)

        # But subclass implementations of visible overloads should still be called.
        self.assertEqual(parent.resolveOverride(s), 'Parent Object')
        self.assertEqual(child.resolveOverride(s), 'Child Object')
        self.assertEqual(cast(Parent, child).resolveOverride(s), 'Child Object')

        with self.assertRaisesRegexp(TypeError, "int object does not specify a Java type"):
            cast(42, child)

        self.assertEqual("Child", child.resolveCovariantOverride())

    def test_primitive(self):
        obj = jclass("com.chaquo.python.TestOverload$Primitive")()

        self.assertEqual(obj.resolve(True), 'boolean true')
        self.assertEqual(obj.resolve(jboolean(True)), 'boolean true')

        self.assertEqual(obj.resolve(42), 'long 42')
        self.assertEqual(obj.resolve(jbyte(42)), 'byte 42')
        self.assertEqual(obj.resolve(jshort(42)), 'short 42')
        self.assertEqual(obj.resolve(jint(42)), 'int 42')
        self.assertEqual(obj.resolve(jlong(42)), 'long 42')

        self.assertEqual(obj.resolve(1.23), 'double 1.23')
        self.assertEqual(obj.resolve(jfloat(1.23)), 'float 1.23')
        self.assertEqual(obj.resolve(jdouble(1.23)), 'double 1.23')

        # When passing an int with integral overloads available, we should never fall back on
        # a float overload no matter how large the value is.
        with self.assertRaisesRegexp(OverflowError, "too (big|large)"):
            obj.resolve_SF(100000)
        self.assertEqual(obj.resolve_SF(42), 'short 42')

        self.assertEqual(obj.resolve_IJ(42), 'long 42')
        self.assertEqual(obj.resolve_IJ(jbyte(42)), 'int 42')
        self.assertEqual(obj.resolve_IJ(jshort(42)), 'int 42')
        self.assertEqual(obj.resolve_IJ(jint(42)), 'int 42')
        self.assertEqual(obj.resolve_IJ(jlong(42)), 'long 42')

        self.assertEqual(obj.resolve_BIF(42), 'int 42')
        self.assertEqual(obj.resolve_BIF(jbyte(42)), 'byte 42')
        self.assertEqual(obj.resolve_BIF(jshort(42)), 'int 42')
        self.assertEqual(obj.resolve_BIF(jint(42)), 'int 42')
        self.assertEqual(obj.resolve_BIF(jlong(42)), 'float 42.0')
        self.assertEqual(obj.resolve_BIF(jfloat(42)), 'float 42.0')
        with self.inapplicable:
            obj.resolve_BIF(jdouble(42))

        # This may seem inconsistent, but it's what Java does. float and double are both
        # applicable, and float is more specific.
        self.assertEqual(obj.resolve_FD(42), 'float 42.0')
        self.assertEqual(obj.resolve_FD(jdouble(42)), 'double 42.0')

    def test_boxing(self):
        obj = jclass("com.chaquo.python.TestOverload$Boxing")()

        Boolean = jclass("java.lang.Boolean")
        self.assertEqual(obj.resolve_Z_Boolean(True), 'boolean true')
        self.assertEqual(obj.resolve_Z_Boolean(jboolean(True)), 'boolean true')
        self.assertEqual(obj.resolve_Z_Boolean(Boolean(True)), 'Boolean true')

        self.assertEqual(obj.resolve_Z_Object(True), 'boolean true')
        self.assertEqual(obj.resolve_Z_Object(jboolean(True)), 'boolean true')
        self.assertEqual(obj.resolve_Z_Object(Boolean(True)), 'Object true')

        Long = jclass("java.lang.Long")
        self.assertEqual(obj.resolve_S_Long(42), 'short 42')
        self.assertEqual(obj.resolve_S_Long(jbyte(42)), 'short 42')
        self.assertEqual(obj.resolve_S_Long(jshort(42)), 'short 42')
        with self.inapplicable:
            # Automatic primitive conversion cannot be combined with autoboxing (JLS 5.3).
            obj.resolve_S_Long(jint(42))
        self.assertEqual(obj.resolve_S_Long(jlong(42)), 'Long 42')
        self.assertEqual(obj.resolve_S_Long(Long(42)), 'Long 42')

        Short = jclass("java.lang.Short")
        self.assertEqual(obj.resolve_Short_L(42), 'long 42')
        self.assertEqual(obj.resolve_Short_L(jbyte(42)), 'long 42')
        self.assertEqual(obj.resolve_Short_L(jshort(42)), 'long 42')
        self.assertEqual(obj.resolve_Short_L(jint(42)), 'long 42')
        self.assertEqual(obj.resolve_Short_L(jlong(42)), 'long 42')
        self.assertEqual(obj.resolve_Short_L(Short(42)), 'Short 42')

        with self.ambiguous:
            obj.resolve_Integer_Long(42)
        with self.inapplicable:
            obj.resolve_Integer_Long(jbyte(42))
        with self.inapplicable:
            obj.resolve_Integer_Long(jshort(42))
        self.assertEqual(obj.resolve_Integer_Long(jint(42)), 'Integer 42')
        self.assertEqual(obj.resolve_Integer_Long(jlong(42)), 'Long 42')

        with self.ambiguous:
            obj.resolve_Integer_Float(42)
        self.assertEqual(obj.resolve_Integer_Float(42.0), 'Float 42.0')
        self.assertEqual(obj.resolve_Integer_Float(jfloat(42)), 'Float 42.0')

        with self.ambiguous:
            obj.resolve_Float_Double(42)
        with self.ambiguous:
            obj.resolve_Float_Double(42.0)
        with self.inapplicable:
            obj.resolve_Float_Double(jint(42))
        self.assertEqual(obj.resolve_Float_Double(jfloat(42)), 'Float 42.0')
        self.assertEqual(obj.resolve_Float_Double(jdouble(42)), 'Double 42.0')

    def test_string(self):
        obj = jclass("com.chaquo.python.TestOverload$TestString")()
        Character = jclass("java.lang.Character")

        self.assertEqual("String x", obj.resolve_String_C_Character("x"))
        self.assertEqual("char x", obj.resolve_String_C_Character(jchar("x")))
        self.assertEqual("Character x", obj.resolve_String_C_Character(Character("x")))

        self.assertEqual("Character x", obj.resolve_Z_Character("x"))

    def test_array(self):
        obj = jclass("com.chaquo.python.TestOverload$TestArray")()

        # Arrays of primitives are always ambiguous, irrespective of the values in the array.
        for l in [None, [True, False], [1, 2]]:
            with self.ambiguous:
                obj.resolve_ZB(l)
        self.assertEqual("boolean[] [true, false]", obj.resolve_ZB(jarray(jboolean)([True, False])))
        self.assertEqual("byte[] [1, 2]", obj.resolve_ZB(jarray(jbyte)([1, 2])))
        self.assertEqual("boolean[] []", obj.resolve_ZB(jarray(jboolean)([])))
        self.assertEqual("byte[] []", obj.resolve_ZB(jarray(jbyte)([])))
        self.assertEqual("boolean[] null", obj.resolve_ZB(jarray(jboolean)(None)))
        self.assertEqual("byte[] null", obj.resolve_ZB(jarray(jbyte)(None)))

        # Arrays of parent/child classes: prefer the most derived class.
        Object = jclass("java.lang.Object")
        Integer = jclass("java.lang.Integer")
        self.assertEqual("Number[] [1, 2]", obj.resolve_Object_Number([1, 2]))
        self.assertEqual("Number[] [1, 2]", obj.resolve_Object_Number(jarray(Integer)([1, 2])))
        self.assertEqual("Object[] [1, 2]", obj.resolve_Object_Number(jarray(Object)([1, 2])))

        # Arrays of sibling classes are always ambiguous.
        Long = jclass("java.lang.Long")
        with self.ambiguous:
            obj.resolve_Integer_Long([1, 2])
        self.assertEqual("Integer[] [1, 2]", obj.resolve_Integer_Long(jarray(Integer)([1, 2])))
        self.assertEqual("Long[] [1, 2]", obj.resolve_Integer_Long(jarray(Long)([1, 2])))

        # Arrays are preferred over Object.
        array_Z = jarray(jboolean)([True, False])
        self.assertEqual("boolean[] null", obj.resolve_Z_Object(None))
        self.assertEqual("Object null", obj.resolve_Z_Object(cast(Object, None)))
        self.assertEqual("boolean[] [true, false]", obj.resolve_Z_Object([True, False]))
        self.assertEqual("boolean[] [true, false]", obj.resolve_Z_Object(array_Z))
        self.assertEqual("Object [true, false]", obj.resolve_Z_Object(cast(Object, array_Z)))
        self.assertEqual("boolean[] [true, false]", obj.resolve_Z_Object(cast(jarray(jboolean),
                                                                              cast(Object, array_Z))))

    def test_varargs(self):
        obj = jclass("com.chaquo.python.TestOverload$Varargs")()

        self.assertEqual("", obj.resolve_empty_single_I())
        self.assertEqual("int... []", obj.resolve_empty_single_I([]))
        self.assertEqual("int... null", obj.resolve_empty_single_I(None))
        self.assertEqual("int 1", obj.resolve_empty_single_I(1))
        self.assertEqual("int... [1]", obj.resolve_empty_single_I([1]))
        self.assertEqual("int... [1, 2]", obj.resolve_empty_single_I(1, 2))
        self.assertEqual("int... [1, 2]", obj.resolve_empty_single_I([1, 2]))

        self.assertEqual("int... []", obj.resolve_ID())  # int is more specific than double.
        with self.ambiguous:
            obj.resolve_ID(None)                         # But int[] is not more specific than double[].
        self.assertEqual("int... null", obj.resolve_ID(jarray(jint)(None)))
        self.assertEqual("double... null", obj.resolve_ID(jarray(jdouble)(None)))
        with self.inapplicable:
            obj.resolve_ID(None, None)
        self.assertEqual("int 42", obj.resolve_ID(42))
        self.assertEqual("double 42.0", obj.resolve_ID(42.0))
        self.assertEqual("double... [1.0, 2.0]", obj.resolve_ID(jarray(jdouble)([1, 2])))
        self.assertEqual("double... [1.0, 2.0]", obj.resolve_ID(1.0, 2.0))
        self.assertEqual("double... [1.0, 2.0]", obj.resolve_ID(1, 2.0))
        self.assertEqual("double... [1.0, 2.0]", obj.resolve_ID(1.0, 2))

        Long = jclass("java.lang.Long")
        with self.ambiguous:
            obj.resolve_I_Long()        # Neither int nor Long are more specific.
        with self.ambiguous:
            obj.resolve_I_Long(None)    # Neither int[] nor Long[] are more specific.
        self.assertEqual("Long... [null, null]", obj.resolve_I_Long(None, None))
        with self.ambiguous:
            obj.resolve_I_Long(42)
        with self.inapplicable:
            obj.resolve_I_Long(42.0)
        self.assertEqual("int... [42]", obj.resolve_I_Long(jint(42)))
        self.assertEqual("Long... [42]", obj.resolve_I_Long(jlong(42)))
        self.assertEqual("Long... [42]", obj.resolve_I_Long(Long(42)))

        Number = jclass("java.lang.Number")
        self.assertEqual("Long... []", obj.resolve_Number_Long())  # Long[] is more specific than Number[].
        self.assertEqual("Long... [42]", obj.resolve_Number_Long(42))
        self.assertEqual("Long... null", obj.resolve_Number_Long(None))
        self.assertEqual("Long... [null]", obj.resolve_Number_Long([None]))
        self.assertEqual("Long... [null, null]", obj.resolve_Number_Long(None, None))
        self.assertEqual("Number... [42]", obj.resolve_Number_Long(cast(Number, Long(42))))
        self.assertEqual("Number... null", obj.resolve_Number_Long(jarray(Number)(None)))
        self.assertEqual("Number... [null]", obj.resolve_Number_Long(cast(Number, None)))
        self.assertEqual("Number... [42]", obj.resolve_Number_Long(jarray(Number)([42])))
        self.assertEqual("Number... [null]", obj.resolve_Number_Long(jarray(Number)([None])))
