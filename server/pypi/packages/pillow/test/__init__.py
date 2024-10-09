import io
from os.path import dirname, join
import unittest


class TestPillow(unittest.TestCase):

    def test_basic(self):
        from PIL import Image

        img = Image.open(join(dirname(__file__), "lena.jpg"))
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

    def test_font(self):
        from PIL import ImageFont
        font = ImageFont.truetype(join(dirname(__file__), "Vera.ttf"), size=20)
        self.assertEqual((0, 4, 51, 19), font.getbbox("Hello"))
        self.assertEqual((0, 4, 112, 19), font.getbbox("Hello world"))
