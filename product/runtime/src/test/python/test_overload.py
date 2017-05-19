from __future__ import absolute_import, division, print_function
import unittest
from chaquopy import autoclass, cast


class TestOverload(unittest.TestCase):

    def test_constructors(self):
        String = autoclass('java.lang.String')
        self.assertEqual("", String())
        self.assertEqual("Hello World", String('Hello World'))
        self.assertEqual("Hello World", String(list('Hello World')))
        self.assertEqual("lo Wo", String(list('Hello World'), 3, 5))

    def test_basic(self):
        basic = autoclass("com.chaquo.python.Overload$Basic")()
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
        MSI = autoclass("com.chaquo.python.Overload$MixedStaticInstance")
        with self.assertRaisesRegexp(AttributeError, "static context"):
            MSI.resolve("two")
        self.assertEqual(MSI().resolve("two"), 'String')

    def test_more_specific_class(self):
        Parent = autoclass("com.chaquo.python.Overload$Parent")
        Child = autoclass("com.chaquo.python.Overload$Child")
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

    def test_more_specific_primitive(self):
        msp = autoclass("com.chaquo.python.Overload$Primitive")()
        self.assertEqual(msp.resolve(True), 'boolean')
        self.assertEqual(msp.resolve(42), 'long')
        self.assertEqual(msp.resolve(1.23), 'double')
        self.assertEqual(msp.resolve("x"), 'String')

        # This may seem wrong, but it's what Java does. float and double are both applicable,
        # and float is more specific.
        self.assertEqual(msp.resolve_float_double(42), 'float')
