import unittest


class TestBrotli(unittest.TestCase):

    def test_basic(self):
        import brotli
        plain = b"it was the best of times, it was the worst of times"
        compressed = brotli.compress(plain)
        with self.subTest(compressed=compressed.hex()):
            self.assertLess(len(compressed), len(plain))
            self.assertEqual(plain, brotli.decompress(compressed))
