import math
import unittest


class TestUjson(unittest.TestCase):

    def test_basic(self):
        import ujson
        self.assertEqual("3.1415926536", ujson.dumps(math.pi))
        self.assertEqual("3.142", ujson.dumps(math.pi, double_precision=3))
