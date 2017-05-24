from __future__ import absolute_import, division, print_function
import unittest
from chaquopy import *


class TestOverload(unittest.TestCase):

    def test_constructors(self):
        String = autoclass('java.lang.String')
        self.assertEqual("", String())
        self.assertEqual("Hello World", String('Hello World'))
        self.assertEqual("Hello World", String(list('Hello World')))
        self.assertEqual("lo Wo", String(list('Hello World'), 3, 5))

    # FIXME remove once covered elsewhere
    def test_basic(self):
        basic = autoclass("com.chaquo.python.TestOverload$Basic")()
        self.assertEqual(basic.resolve(), '')
        self.assertEqual(basic.resolve('arg'), 'String')
        self.assertEqual(basic.resolve('one', 'two'), 'String, String')
        self.assertEqual(basic.resolve('one', 'two', 1), 'String, String, int')
        self.assertEqual(basic.resolve('one', 'two', 1, 2), 'String, String, int, int')
        self.assertEqual(basic.resolve(1, 2, 3), 'int...')
        self.assertEqual(basic.resolve('one', 'two', 1, 2, 3), 'String, String, int...')

    # Whether a call's in static or instance context should make no difference to the methods
    # considered and chosen during overload resolution.
    def test_mixed_static_and_instance(self):
        MSI = autoclass("com.chaquo.python.TestOverload$MixedStaticInstance")
        with self.assertRaisesRegexp(AttributeError, "static context"):
            MSI.resolve("two")
        self.assertEqual(MSI().resolve("two"), 'String')

    def test_class(self):
        Parent = autoclass("com.chaquo.python.TestOverload$Parent")
        Child = autoclass("com.chaquo.python.TestOverload$Child")
        Object = autoclass("java.lang.Object")
        String = autoclass("java.lang.String")
        Integer = autoclass("java.lang.Integer")
        s = String()
        i = Integer(42)
        child = Child()

        self.assertEqual(child.resolve(s), 'String')
        self.assertEqual(child.resolve(i), 'Integer')
        self.assertEqual(child.resolve(cast(Object, s)), 'Object')

        self.assertEqual(child.resolve(s, i), 'String, Object')
        self.assertEqual(child.resolve(i, s), 'Object, String')
        with self.assertRaisesRegexp(TypeError, "cannot be applied to"):
            child.resolve(i, i)

        # Casting of method parameters
        with self.assertRaisesRegexp(TypeError, "ambiguous"):
            child.resolve(s, s)
        self.assertEqual(child.resolve(cast(Object, s), s), 'Object, String')
        self.assertEqual(child.resolve(s, cast(Object, s)), 'String, Object')

        # Casting of object on which method is called
        self.assertEqual(cast(Parent, child).resolve(s), 'Object')
        self.assertEqual(cast(Parent, child).resolve(s, s), 'Object, String')
        with self.assertRaisesRegexp(TypeError, "cannot be applied to"):
            cast(Parent, child).resolve(s, i)

        with self.assertRaisesRegexp(TypeError, "Java class"):
            cast(42, child)

    def test_primitive(self):
        obj = autoclass("com.chaquo.python.TestOverload$Primitive")()

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

        self.assertEqual(obj.resolve_BIF(42), 'int 42')
        self.assertEqual(obj.resolve_BIF(jbyte(42)), 'byte 42')
        self.assertEqual(obj.resolve_BIF(jshort(42)), 'int 42')
        self.assertEqual(obj.resolve_BIF(jint(42)), 'int 42')
        self.assertEqual(obj.resolve_BIF(jlong(42)), 'float 42.0')
        self.assertEqual(obj.resolve_BIF(jfloat(42)), 'float 42.0')
        with self.assertRaisesRegexp(TypeError, "cannot be applied"):
            obj.resolve_BIF(jdouble(42))

        self.assertEqual(obj.resolve("x"), 'String x')
        self.assertEqual(obj.resolve(jchar("x")), 'char x')

        # This may seem inconsistent, but it's what Java does. float and double are both
        # applicable, and float is more specific.
        self.assertEqual(obj.resolve_FD(42), 'float 42.0')
        self.assertEqual(obj.resolve_FD(jdouble(42)), 'double 42.0')

    def test_boxing(self):
        obj = autoclass("com.chaquo.python.TestOverload$Boxing")()

        Boolean = autoclass("java.lang.Boolean")
        self.assertEqual(obj.resolve_Z_Boolean(True), 'boolean true')
        self.assertEqual(obj.resolve_Z_Boolean(jboolean(True)), 'boolean true')
        self.assertEqual(obj.resolve_Z_Boolean(Boolean(True)), 'Boolean true')

        self.assertEqual(obj.resolve_Z_Object(True), 'boolean true')
        self.assertEqual(obj.resolve_Z_Object(jboolean(True)), 'boolean true')
        self.assertEqual(obj.resolve_Z_Object(Boolean(True)), 'Object true')

        Long = autoclass("java.lang.Long")
        self.assertEqual(obj.resolve_S_Long(42), 'short 42')
        self.assertEqual(obj.resolve_S_Long(jbyte(42)), 'short 42')
        self.assertEqual(obj.resolve_S_Long(jshort(42)), 'short 42')
        with self.assertRaisesRegexp(TypeError, "cannot be applied"):
            # Automatic primitive conversion cannot be combined with autoboxing (JLS 5.3).
            obj.resolve_S_Long(jint(42))
        self.assertEqual(obj.resolve_S_Long(jlong(42)), 'Long 42')
        self.assertEqual(obj.resolve_S_Long(Long(42)), 'Long 42')

        Short = autoclass("java.lang.Short")
        self.assertEqual(obj.resolve_Short_L(42), 'long 42')
        self.assertEqual(obj.resolve_Short_L(jbyte(42)), 'long 42')
        self.assertEqual(obj.resolve_Short_L(jshort(42)), 'long 42')
        self.assertEqual(obj.resolve_Short_L(jint(42)), 'long 42')
        self.assertEqual(obj.resolve_Short_L(jlong(42)), 'long 42')
        self.assertEqual(obj.resolve_Short_L(Short(42)), 'Short 42')

        with self.assertRaisesRegexp(TypeError, "ambiguous"):
            obj.resolve_Integer_Long(42)
        with self.assertRaisesRegexp(TypeError, "cannot be applied"):
            obj.resolve_Integer_Long(jbyte(42))
        with self.assertRaisesRegexp(TypeError, "cannot be applied"):
            obj.resolve_Integer_Long(jshort(42))
        self.assertEqual(obj.resolve_Integer_Long(jint(42)), 'Integer 42')
        self.assertEqual(obj.resolve_Integer_Long(jlong(42)), 'Long 42')

    def test_string(self):
        pass
        # FIXME a string can be converted to String, char, Character, char[] and Character[].

    def test_array(self):
        pass
        # FIXME can pass None, with or without jarray wrapper.
