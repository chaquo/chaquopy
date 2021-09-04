import unittest


class TestGoogleCrc32c(unittest.TestCase):

    # Based on https://github.com/googleapis/python-crc32c/blob/main/tests/test___init__.py
    def test_basic(self):
        import google_crc32c

        self.assertEqual("c", google_crc32c.implementation)
        for data, expected in [(b"", 0x00000000),
                               (b"\x00" * 32, 0x8A9136AA),
                               (bytes(range(32)), 0x46DD794E)]:
            with self.subTest(data=data):
                self.assertEqual(expected, google_crc32c.value(data))
