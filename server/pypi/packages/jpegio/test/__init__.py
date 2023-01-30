from os.path import dirname
import unittest


class TestJpegIO(unittest.TestCase):

    def test_basic(self):
        import jpegio
        img = jpegio.read(f"{dirname(__file__)}/tiger.jpg")
        self.assertEqual((800, 533), (img.image_width, img.image_height))
        self.assertEqual((536, 800), img.coef_arrays[0].shape)
