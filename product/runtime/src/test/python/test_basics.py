from __future__ import absolute_import, division, print_function
import unittest
from chaquopy import autoclass


class BasicsTest(unittest.TestCase):

    def test_static_methods(self):
        Test = autoclass('com.chaquo.python.BasicsTest')
        self.assertEquals(Test.methodStaticZ(), True)
        self.assertEquals(Test.methodStaticB(), 127)
        self.assertEquals(Test.methodStaticC(), 'k')
        self.assertEquals(Test.methodStaticS(), 32767)
        self.assertEquals(Test.methodStaticI(), 2147483467)
        self.assertEquals(Test.methodStaticJ(), 9223372036854775807)
        self.assertAlmostEquals(Test.methodStaticF(), 1.23456789)
        self.assertAlmostEquals(Test.methodStaticD(), 1.23456789)
        self.assertEquals(Test.methodStaticString(), 'staticworld')
        self.assertEquals(Test.methodStaticParamsString("foo"), 'foo')

        # Static methods can also be accessed on an instance
        t = Test()
        self.assertEquals(t.methodStaticString(), 'staticworld')
        self.assertEquals(t.methodStaticI(), 2147483467)
        self.assertEquals(t.methodStaticParamsString("foo"), 'foo')
        with self.assertRaisesRegexp(AttributeError, "not a field"):
            t.methodStaticParamsString = 99

        with self.assertRaisesRegexp(AttributeError, "has no attribute"):
            Test.methodStaticNonexistent()
        with self.assertRaisesRegexp(TypeError, "takes 0 arguments"):
            Test.methodStaticString("foo")
        with self.assertRaisesRegexp(TypeError, "takes 1 argument"):
            Test.methodStaticParamsString()
        with self.assertRaisesRegexp(AttributeError, "not a field"):
            Test.methodStaticParamsString = 99

    def test_static_get_fields(self):
        Test = autoclass('com.chaquo.python.BasicsTest')
        self.assertEquals(Test.fieldStaticZ, True)
        self.assertEquals(Test.fieldStaticB, 127)
        self.assertEquals(Test.fieldStaticC, 'k')
        self.assertEquals(Test.fieldStaticS, 32767)
        self.assertEquals(Test.fieldStaticI, 2147483467)
        self.assertEquals(Test.fieldStaticJ, 9223372036854775807)
        self.assertAlmostEquals(Test.fieldStaticF, 1.23456789)
        self.assertAlmostEquals(Test.fieldStaticD, 1.23456789)
        self.assertEquals(Test.fieldStaticString, 'staticworld')
        # FIXME add array fields to this and other field tests

        # Static fields can also be accessed on an instance
        t = Test()
        self.assertEquals(t.fieldStaticString, 'staticworld')
        self.assertEquals(t.fieldStaticI, 2147483467)

        with self.assertRaisesRegexp(AttributeError, "has no attribute"):
            Test.fieldStaticNonexistent

    def test_static_set_fields(self):
        Test = autoclass('com.chaquo.python.BasicsTest')
        Test.fieldStaticZ = False
        Test.fieldStaticB = -127
        Test.fieldStaticC = 'p'
        Test.fieldStaticS = -32767
        Test.fieldStaticI = -2147483467
        Test.fieldStaticJ = -9223372036854775807
        Test.fieldStaticF = -1.23456789
        Test.fieldStaticD = -9.87654321
        Test.fieldStaticString = "setstaticworld"

        self.assertEquals(Test.fieldStaticZ, False)
        self.assertEquals(Test.fieldStaticB, -127)
        self.assertEquals(Test.fieldStaticC, 'p')
        self.assertEquals(Test.fieldStaticS, -32767)
        self.assertEquals(Test.fieldStaticI, -2147483467)
        self.assertEquals(Test.fieldStaticJ, -9223372036854775807)
        self.assertAlmostEquals(Test.fieldStaticF, -1.23456789)
        self.assertAlmostEquals(Test.fieldStaticD, -9.87654321)
        self.assertEquals(Test.fieldStaticString, 'setstaticworld')

        # Check new value is visible in Java as well
        self.assertEquals(Test.methodStaticZ(), False)
        self.assertEquals(Test.methodStaticB(), -127)
        self.assertEquals(Test.methodStaticC(), 'p')
        self.assertEquals(Test.methodStaticS(), -32767)
        self.assertEquals(Test.methodStaticI(), -2147483467)
        self.assertEquals(Test.methodStaticJ(), -9223372036854775807)
        self.assertAlmostEquals(Test.methodStaticF(), -1.23456789)
        self.assertAlmostEquals(Test.methodStaticD(), -9.87654321)
        self.assertEquals(Test.methodStaticString(), 'setstaticworld')

        with self.assertRaisesRegexp(AttributeError, "has no attribute"):
            Test.fieldStaticNonexistent = 99
        with self.assertRaisesRegexp(AttributeError, "final"):
            Test.fieldStaticFinalString = "notfinal"
        self.assertEquals(Test.fieldStaticFinalString, 'staticfinalworld')

        # Static fields can also be accessed on an instance
        t = Test()
        t2 = Test()
        t.fieldStaticString = "setinstanceworld"
        self.assertEquals(t.fieldStaticString, 'setinstanceworld')
        self.assertEquals(t2.fieldStaticString, 'setinstanceworld')
        self.assertEquals(Test.fieldStaticString, 'setinstanceworld')
        self.assertEquals(Test.methodStaticString(), 'setinstanceworld')
        t2.fieldStaticI = 42
        self.assertEquals(t.fieldStaticI, 42)
        self.assertEquals(t2.fieldStaticI, 42)
        self.assertEquals(Test.fieldStaticI, 42)
        self.assertEquals(Test.methodStaticI(), 42)

    def test_instance_methods(self):
        Test = autoclass('com.chaquo.python.BasicsTest')
        test = Test()
        self.assertEquals(test.methodZ(), True)
        self.assertEquals(test.methodB(), 127)
        self.assertEquals(test.methodC(), 'k')
        self.assertEquals(test.methodS(), 32767)
        self.assertEquals(test.methodI(), 2147483467)
        self.assertEquals(test.methodJ(), 9223372036854775807)
        self.assertAlmostEquals(test.methodF(), 1.23456789)
        self.assertAlmostEquals(test.methodD(), 9.87654321)
        self.assertEquals(test.methodString(), 'helloworld')

        with self.assertRaisesRegexp(AttributeError, "has no attribute"):
            test.methodNonexistent()
        with self.assertRaisesRegexp(TypeError, "takes 0 arguments"):
            test.methodString("foo")
        with self.assertRaisesRegexp(TypeError, "takes 1 argument"):
            test.methodParamsString()
        with self.assertRaisesRegexp(AttributeError, "static context"):
            Test.methodString()
        with self.assertRaisesRegexp(AttributeError, "not a field"):
            test.methodString = 99

    def test_instance_methods_multiple_instances(self):
        BT = autoclass('com.chaquo.python.BasicsTest')
        test1, test2 = BT(), BT(10)
        self.assertEquals(test2.methodB(), 10)
        self.assertEquals(test1.methodB(), 127)
        self.assertEquals(test2.methodB(), 10)
        method1 = test1.methodB
        method2 = test2.methodB
        self.assertEquals(method1(), 127)
        self.assertEquals(method2(), 10)
        self.assertEquals(method1(), 127)

        # Instantiation of a new object shouldn't affect methods already bound.
        test3 = BT(42)
        self.assertEquals(method1(), 127)
        self.assertEquals(method2(), 10)

    def test_instance_get_fields(self):
        Test = autoclass('com.chaquo.python.BasicsTest')
        test = Test()
        self.assertEquals(test.fieldZ, True)
        self.assertEquals(test.fieldB, 127)
        self.assertEquals(test.fieldC, 'k')
        self.assertEquals(test.fieldS, 32767)
        self.assertEquals(test.fieldI, 2147483467)
        self.assertEquals(test.fieldJ, 9223372036854775807)
        self.assertAlmostEquals(test.fieldF, 1.23456789)
        self.assertAlmostEquals(test.fieldD, 9.87654321)
        self.assertEquals(test.fieldString, 'helloworld')

        with self.assertRaisesRegexp(AttributeError, "has no attribute"):
            test.fieldNonexistent
        with self.assertRaisesRegexp(AttributeError, "static context"):
            Test.fieldString

    def test_instance_fields_multiple_instances(self):
        BT = autoclass('com.chaquo.python.BasicsTest')
        test1, test2 = BT(), BT(10)
        self.assertEquals(test2.fieldB, 10)
        self.assertEquals(test1.fieldB, 127)
        self.assertEquals(test2.fieldB, 10)

        test1.fieldB = 11
        test2.fieldB = 22
        self.assertEquals(test1.fieldB, 11)
        self.assertEquals(test2.fieldB, 22)
        self.assertEquals(test1.methodB(), 11)
        self.assertEquals(test2.methodB(), 22)

    def test_instance_set_fields(self):
        Test = autoclass('com.chaquo.python.BasicsTest')
        test = Test()
        test.fieldZ = False
        test.fieldB = -127
        test.fieldC = 'p'
        test.fieldS = -32767
        test.fieldI = -2147483467
        test.fieldJ = -9223372036854775807
        test.fieldF = -1.23456789
        test.fieldD = -9.87654321
        test.fieldString = "setworld"

        self.assertEquals(test.fieldZ, False)
        self.assertEquals(test.fieldB, -127)
        self.assertEquals(test.fieldC, 'p')
        self.assertEquals(test.fieldS, -32767)
        self.assertEquals(test.fieldI, -2147483467)
        self.assertEquals(test.fieldJ, -9223372036854775807)
        self.assertAlmostEquals(test.fieldF, -1.23456789)
        self.assertAlmostEquals(test.fieldD, -9.87654321)
        self.assertEquals(test.fieldString, 'setworld')

        # Check new value is visible in Java as well
        self.assertEquals(test.methodZ(), False)
        self.assertEquals(test.methodB(), -127)
        self.assertEquals(test.methodC(), 'p')
        self.assertEquals(test.methodS(), -32767)
        self.assertEquals(test.methodI(), -2147483467)
        self.assertEquals(test.methodJ(), -9223372036854775807)
        self.assertAlmostEquals(test.methodF(), -1.23456789)
        self.assertAlmostEquals(test.methodD(), -9.87654321)
        self.assertEquals(test.methodString(), 'setworld')

        with self.assertRaisesRegexp(AttributeError, "has no attribute"):
            test.fieldNonexistent = 99
        with self.assertRaisesRegexp(AttributeError, "final"):
            test.fieldFinalString = "notfinal"
        self.assertEquals(test.fieldFinalString, 'finalworld')
        with self.assertRaisesRegexp(AttributeError, "static context"):
            Test.fieldString = 42

    def test_instance_methods_array(self):
        test = autoclass('com.chaquo.python.BasicsTest')()
        # FIXME test full range of each type
        self.assertEquals(test.methodArrayZ(), [True] * 3)
        self.assertEquals(test.methodArrayB(), [127] * 3)
        self.assertEquals(test.methodArrayC(), ['k'] * 3)
        self.assertEquals(test.methodArrayS(), [32767] * 3)
        self.assertEquals(test.methodArrayI(), [2147483467] * 3)
        self.assertEquals(test.methodArrayJ(), [9223372036854775807] * 3)

        ret = test.methodArrayF()
        ref = [1.23456789] * 3
        self.assertAlmostEquals(ret[0], ref[0])
        self.assertAlmostEquals(ret[1], ref[1])
        self.assertAlmostEquals(ret[2], ref[2])

        self.assertEquals(test.methodArrayD(), [1.23456789] * 3)
        self.assertEquals(test.methodArrayString(), ['helloworld'] * 3)

    def test_instance_methods_params(self):
        test = autoclass('com.chaquo.python.BasicsTest')()
        self.assertEquals(test.methodParamsZBCSIJFD(
            True, 127, 'k', 32767, 2147483467, 9223372036854775807, 1.23456789, 1.23456789), True)
        self.assertEquals(test.methodParamsString('helloworld'), True)
        self.assertEquals(test.methodParamsArrayI([1, 2, 3]), True)
        self.assertEquals(test.methodParamsArrayString([
            'hello', 'world']), True)

    def test_instance_methods_params_object_list_str(self):
        test = autoclass('com.chaquo.python.BasicsTest')()
        self.assertEquals(test.methodParamsObject([
            'hello', 'world']), True)

    def test_instance_methods_params_object_list_int(self):
        test = autoclass('com.chaquo.python.BasicsTest')()
        self.assertEquals(test.methodParamsObject([1, 2]), True)

    def test_instance_methods_params_object_list_float(self):
        test = autoclass('com.chaquo.python.BasicsTest')()
        self.assertEquals(test.methodParamsObject([3.14, 1.61]), True)

    def test_instance_methods_params_object_list_long(self):
        test = autoclass('com.chaquo.python.BasicsTest')()
        self.assertEquals(test.methodParamsObject([1, 2]), True)

    def test_instance_methods_params_array_byte(self):
        test = autoclass('com.chaquo.python.BasicsTest')()
        self.assertEquals(test.methodParamsArrayByte([127, 127, 127]), True)
        ret = test.methodArrayB()
        self.assertEquals(test.methodParamsArrayByte(ret), True)

    def test_return_array_as_object_array_of_strings(self):
        test = autoclass('com.chaquo.python.BasicsTest')()
        self.assertEquals(test.methodReturnStrings(), ['Hello', 'world'])

    def test_return_array_as_object_of_integers(self):
        test = autoclass('com.chaquo.python.BasicsTest')()
        self.assertEquals(test.methodReturnIntegers(), [1, 2])
