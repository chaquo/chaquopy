from __future__ import absolute_import, division, print_function
import ctypes
import unittest
from chaquopy import autoclass


class TestArrays(unittest.TestCase):

    def test_output_arg(self):
        String = autoclass('java.lang.String')
        string = String(u'\u1156\u2278\u3390\u44AB')
        btarray = [0] * 4
        # This version of getBytes returns the 8 low-order of each Unicode character.
        string.getBytes(0, 4, btarray, 0)
        self.assertEquals(btarray, [ctypes.c_int8(x).value for x in [0x56, 0x78, 0x90, 0xAB]])

    def test_multiple_dimensions(self):
        Arrays = autoclass('com.chaquo.python.TestArrays')
        matrix = [[1, 2, 3],
                  [4, 5, 6],
                  [7, 8, 9]]
        self.assertEquals(Arrays.methodParamsMatrixI(matrix), True)
        self.assertEquals(Arrays.methodReturnMatrixI(), matrix)
