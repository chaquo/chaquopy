from __future__ import absolute_import, division, print_function

import unittest


class TestPillow(unittest.TestCase):

    def test_basic(self):
        import io
        from PIL import Image
        import pkgutil

        in_file = io.BytesIO(pkgutil.get_data(__name__, "lena.jpg"))
        img = Image.open(in_file)
        self.assertEqual(512, img.width)
        self.assertEqual(512, img.height)

        out_file = io.BytesIO()
        img.save(out_file, "png")
        out_bytes = out_file.getvalue()

        EXPECTED_LEN = 313772
        self.assertGreater(len(out_bytes), int(EXPECTED_LEN * 0.8))
        self.assertLess(len(out_bytes), int(EXPECTED_LEN * 1.2))

        self.assertEqual(b"\x89PNG\r\n\x1a\n" +     # File header
                         b"\x00\x00\x00\rIHDR" +    # Header chunk header
                         b"\x00\x00\x02\x00" +      # Width 512
                         b"\x00\x00\x02\x00",       # Height 512
                         out_bytes[:24])
