from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import unittest
from chaquopy.reflect import autoclass
from chaquopy import cast


class TestCast(unittest.TestCase):

    def test_cast(self):
        String = autoclass('java.lang.String')
        s = String('hello world')
        self.assertEquals(s.__javaclass__, 'java.lang.String')
        self.assertTrue(hasattr(s, "substring"))

        o = cast('java.lang.Object', s)
        self.assertEquals(o.__javaclass__, 'java.lang.Object')
        self.assertFalse(hasattr(o, "substring"))

        with self.assertRaises(TypeError):
            cast('java.lang.Integer', s)
