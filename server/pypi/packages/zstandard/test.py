import unittest


class TestZstandard(unittest.TestCase):

    def test_basic(self):
        import zstandard

        self.assertEqual(
            b'(\xb5/\xfd l\x1d\x02\x00$\x03It was the best of times, iworagewisdomfoolishness'
            b'\x05\x00=3\x80\xd5\x15\x9e\xc1\xf0\t\xc6\r\xcf1',
            zstandard.compress(b"It was the best of times, it was the worst of times, "
                               b"it was the age of wisdom, it was the age of foolishness"))

        self.assertEqual(
            b"It is a far, far better thing that I do, than I have ever done; "
            b"it is a far, far better rest that I go to than I have ever known.",
            zstandard.decompress(
                b"(\xb5/\xfd \x81]\x02\x00\x82D\x0e\x14\xa0\xa5\xe9\x04dW.\xffM\xc8oe\x14\x04\xa3"
                b"\xd3v\xf8\xbfj\xc2\r\xf0\x04\xd8\xb1\x14Y\x9e\x07;$\xa7%\xdbR\x99\xc7'\x90<n\x99^"
                b"\xee\x98\x9e\xd6\x1a`\x91\x15\xb8F\xe7\x8e\x05\x00Dx-\x04A\x0e\xa1\x18.<\xb0\x16:"))
