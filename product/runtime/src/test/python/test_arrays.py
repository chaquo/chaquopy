from __future__ import absolute_import, division, print_function
import unittest
from chaquopy import autoclass


class TestArrays(unittest.TestCase):

    def test_fill_byte_array(self):
        arr = [0, 0, 0]
        Test = autoclass('com.chaquo.python.Basics')()
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
        Arrays = autoclass('com.chaquo.python.Arrays')
        matrix = [[1, 2, 3],
                  [4, 5, 6],
                  [7, 8, 9]]
        self.assertEquals(Arrays.methodParamsMatrixI(matrix), True)
        self.assertEquals(Arrays.methodReturnMatrixI(), matrix)
