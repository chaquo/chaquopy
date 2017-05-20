from __future__ import absolute_import, division, print_function
import unittest
from chaquopy import autoclass


class TestArrays(unittest.TestCase):

    def test_instance_methods_array(self):
        test = autoclass('com.chaquo.python.TestArrays')()
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
        test = autoclass('com.chaquo.python.TestArrays')()
        self.assertEquals(test.methodParamsZBCSIJFD(
            True, 127, 'k', 32767, 2147483467, 9223372036854775807, 1.23456789, 1.23456789), True)
        self.assertEquals(test.methodParamsArrayI([1, 2, 3]), True)
        self.assertEquals(test.methodParamsArrayString([
            'hello', 'world']), True)

    def test_instance_methods_params_object_list_str(self):
        test = autoclass('com.chaquo.python.TestArrays')()
        self.assertEquals(test.methodParamsObject([
            'hello', 'world']), True)

    def test_instance_methods_params_object_list_int(self):
        test = autoclass('com.chaquo.python.TestArrays')()
        self.assertEquals(test.methodParamsObject([1, 2]), True)

    def test_instance_methods_params_object_list_float(self):
        test = autoclass('com.chaquo.python.TestArrays')()
        self.assertEquals(test.methodParamsObject([3.14, 1.61]), True)

    def test_instance_methods_params_object_list_long(self):
        test = autoclass('com.chaquo.python.TestArrays')()
        self.assertEquals(test.methodParamsObject([1, 2]), True)

    def test_instance_methods_params_array_byte(self):
        test = autoclass('com.chaquo.python.TestArrays')()
        self.assertEquals(test.methodParamsArrayByte([127, 127, 127]), True)
        ret = test.methodArrayB()
        self.assertEquals(test.methodParamsArrayByte(ret), True)

    def test_return_array_as_object_array_of_strings(self):
        test = autoclass('com.chaquo.python.TestArrays')()
        self.assertEquals(test.methodReturnStrings(), ['Hello', 'world'])

    def test_return_array_as_object_of_integers(self):
        test = autoclass('com.chaquo.python.TestArrays')()
        self.assertEquals(test.methodReturnIntegers(), [1, 2])

    def test_fill_byte_array(self):
        arr = [0, 0, 0]
        Test = autoclass('com.chaquo.python.TestArrays')()
        Test.fillByteArray(arr)
        # we don't received signed byte, but unsigned in python (FIXME think about this)
        self.assertEquals(
            arr,
            [127, 1, 129])

    def test_create_bytearray(self):
        StringBufferInputStream = autoclass('java.io.StringBufferInputStream')
        nis = StringBufferInputStream("Hello world")
        barr = bytearray("\x00" * 5, encoding="utf8")
        self.assertEquals(nis.read(barr, 0, 5), 5)
        self.assertEquals(barr, b"Hello")

    def test_bytearray_ascii(self):
        ByteArrayInputStream = autoclass('java.io.ByteArrayInputStream')
        s = b"".join(bytes(x) for x in range(256))
        nis = ByteArrayInputStream(bytearray(s))
        barr = bytearray("\x00" * 256, encoding="ascii")
        self.assertEquals(nis.read(barr, 0, 256), 256)
        self.assertEquals(barr[:256], s[:256])

    def test_output_args(self):
        String = autoclass('java.lang.String')
        string = String('word'.encode('utf-8'))
        btarray= [0] * 4
        string.getBytes(0, 4, btarray, 0)
        self.assertEquals(btarray, [119, 111, 114, 100])

    def test_multiple_dimensions(self):
        Arrays = autoclass('com.chaquo.python.TestArrays')
        matrix = [[1, 2, 3],
                  [4, 5, 6],
                  [7, 8, 9]]
        self.assertEquals(Arrays.methodParamsMatrixI(matrix), True)
        self.assertEquals(Arrays.methodReturnMatrixI(), matrix)
