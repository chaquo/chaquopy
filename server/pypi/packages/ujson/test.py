import math
import unittest


class TestUjson(unittest.TestCase):

    def test_basic(self):
        import ujson
        self.assertEqual(ujson.dumps(math.pi), "3.141592653589793")

        script = "<script>John&Doe"
        self.assertEqual(ujson.dumps(script), f'"{script}"')
        self.assertEqual(
            ujson.dumps(script, encode_html_chars=True),
            '"\\u003cscript\\u003eJohn\\u0026Doe"'
        )
