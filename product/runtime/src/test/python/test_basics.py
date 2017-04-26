from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import unittest
from chaquopy.reflect import autoclass

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
        self.assertEquals(Test.methodStaticD(), 1.23456789)
        self.assertEquals(Test.methodStaticString(), 'helloworld')

        # Static methods can also be accessed on an instance
        t = Test()
        self.assertEquals(t.methodStaticString(), 'helloworld')
        self.assertEquals(t.methodStaticI(), 2147483467)

    def test_static_fields(self):
        Test = autoclass('com.chaquo.python.BasicsTest')
        self.assertEquals(Test.fieldStaticZ, True)
        self.assertEquals(Test.fieldStaticB, 127)
        self.assertEquals(Test.fieldStaticC, 'k')
        self.assertEquals(Test.fieldStaticS, 32767)
        self.assertEquals(Test.fieldStaticI, 2147483467)
        self.assertEquals(Test.fieldStaticJ, 9223372036854775807)
        self.assertAlmostEquals(Test.fieldStaticF, 1.23456789)
        self.assertEquals(Test.fieldStaticD, 1.23456789)
        self.assertEquals(Test.fieldStaticString, 'helloworld')
        # FIXME add array fields to this and other field tests

        # Static fields can also be accessed on an instance
        t = Test()
        self.assertEquals(t.fieldStaticString, 'helloworld')
        self.assertEquals(t.fieldStaticI, 2147483467)

    def test_static_set_fields(self):
        pass    # FIXME not implemented yet
        # FIXME test what happens setting a final field: probably raises a Java exception, so no
        # special action required.

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
        self.assertEquals(test.methodD(), 1.23456789)
        self.assertEquals(test.methodString(), 'helloworld')

    def test_instance_methods_unbound(self):
        # Instance methods can be called on the class by passing an instance as the first argument.
        Test = autoclass('com.chaquo.python.BasicsTest')
        test = Test()
        with self.assertRaises(TypeError):
            Test.methodString()
        with self.assertRaises(TypeError):
            Test.methodString(99)
        self.assertEquals(Test.methodString(test), 'helloworld')

        with self.assertRaises(TypeError):
            Test.methodParamsString('helloworld')
        self.assertEquals(Test.methodParamsString(test, 'helloworld'), True)

    def test_instance_methods_multiple(self):
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

        # Instantiation shouldn't rebind existing methods
        test3 = BT(42)
        self.assertEquals(method1(), 127)
        self.assertEquals(method2(), 10)

    def test_instance_fields(self):
        Test = autoclass('com.chaquo.python.BasicsTest')
        test = Test()
        self.assertEquals(test.fieldZ, True)
        self.assertEquals(test.fieldB, 127)
        self.assertEquals(test.fieldC, 'k')
        self.assertEquals(test.fieldS, 32767)
        self.assertEquals(test.fieldI, 2147483467)
        self.assertEquals(test.fieldJ, 9223372036854775807)
        self.assertAlmostEquals(test.fieldF, 1.23456789)
        self.assertEquals(test.fieldD, 1.23456789)
        self.assertEquals(test.fieldString, 'helloworld')

        # Instance fields cannot be accessed in a static context
        with self.assertRaises(AttributeError):
            Test.fieldString

    def test_instance_fields_multiple(self):
        BT = autoclass('com.chaquo.python.BasicsTest')
        test1, test2 = BT(), BT(10)
        self.assertEquals(test2.fieldB, 10)
        self.assertEquals(test1.fieldB, 127)
        self.assertEquals(test2.fieldB, 10)

        test1.fieldB = 11
        test2.fieldB = 22
        self.assertEquals(test1.fieldB, 11)
        self.assertEquals(test2.fieldB, 22)

    def test_instance_set_fields(self):
        Test = autoclass('com.chaquo.python.BasicsTest')
        test = Test()
        test.fieldSetZ = True
        test.fieldSetB = 127
        test.fieldSetC = ord('k')
        test.fieldSetS = 32767
        test.fieldSetI = 2147483467
        test.fieldSetJ = 9223372036854775807
        test.fieldSetF = 1.23456789
        test.fieldSetD = 1.23456789

        self.assertTrue(test.testFieldSetZ())
        self.assertTrue(test.testFieldSetB())
        self.assertTrue(test.testFieldSetC())
        self.assertTrue(test.testFieldSetS())
        self.assertTrue(test.testFieldSetI())
        self.assertTrue(test.testFieldSetJ())
        self.assertTrue(test.testFieldSetF())
        self.assertTrue(test.testFieldSetD())

        # FIXME Instance fields cannot be accessed in a static context
        # with self.assertRaises(AttributeError):
        #    Test.fieldSetI = 42

        # FIXME test what happens setting a final field: probably raises a Java exception, so no
        # special action required.

    def test_instances_methods_array(self):
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

    def test_instances_methods_params(self):
        test = autoclass('com.chaquo.python.BasicsTest')()
        self.assertEquals(test.methodParamsZBCSIJFD(
            True, 127, 'k', 32767, 2147483467, 9223372036854775807, 1.23456789, 1.23456789), True)
        self.assertEquals(test.methodParamsString('helloworld'), True)
        self.assertEquals(test.methodParamsArrayI([1, 2, 3]), True)
        self.assertEquals(test.methodParamsArrayString([
            'hello', 'world']), True)

    def test_instances_methods_params_object_list_str(self):
        test = autoclass('com.chaquo.python.BasicsTest')()
        self.assertEquals(test.methodParamsObject([
            'hello', 'world']), True)

    def test_instances_methods_params_object_list_int(self):
        test = autoclass('com.chaquo.python.BasicsTest')()
        self.assertEquals(test.methodParamsObject([1, 2]), True)

    def test_instances_methods_params_object_list_float(self):
        test = autoclass('com.chaquo.python.BasicsTest')()
        self.assertEquals(test.methodParamsObject([3.14, 1.61]), True)

    def test_instances_methods_params_object_list_long(self):
        test = autoclass('com.chaquo.python.BasicsTest')()
        self.assertEquals(test.methodParamsObject([1, 2]), True)

    def test_instances_methods_params_array_byte(self):
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
