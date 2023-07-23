import unittest


class TestMultidict(unittest.TestCase):

    def test_basic(self):
        import os
        import lz4.frame
        input_data = 20 * 128 * os.urandom(1024)
        compressed = lz4.frame.compress(input_data)
        decompressed = lz4.frame.decompress(compressed)
        unittest.assertEqual(decompressed, input_data)

