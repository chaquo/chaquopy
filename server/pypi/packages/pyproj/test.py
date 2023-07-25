import unittest


class TestPyproj(unittest.TestCase):

    # https://pyproj4.github.io/pyproj/stable/examples.html#step-2-create-transformer-to-convert-from-crs-to-crs
    def test_basic(self):
        from pyproj import Transformer
        transformer = Transformer.from_crs(4326, 26917)
        self.assertEqual(
            [round(x) for x in transformer.transform(50, -80)],
            [571666, 5539110]
        )
