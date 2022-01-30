from os.path import dirname
import unittest


class TestPyzbar(unittest.TestCase):

    # See https://github.com/NaturalHistoryMuseum/pyzbar/blob/master/README.rst
    def test_basic(self):
        from PIL import Image
        from pyzbar import pyzbar

        result = pyzbar.decode(Image.open(f"{dirname(__file__)}/qrcode.png"))
        self.assertEqual(1, len(result))
        self.assertEqual(b"Thalassiodracon", result[0].data)
