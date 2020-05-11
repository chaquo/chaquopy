import unittest


class TestMatplotlib(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            from android.os import Build  # noqa: F401
        except ImportError:
            # On Android, the non-interactive backend should be used by default. On Debian, we
            # have to enable it explicitly.
            import matplotlib
            matplotlib.use('agg')

    def test_png(self):
        import io
        import matplotlib.pyplot as plt

        plt.figure()
        plt.plot([1, 2])
        bio = io.BytesIO()
        plt.savefig(bio, format="png")
        b = bio.getvalue()

        EXPECTED_LEN = 16782
        self.assertGreater(len(b), int(EXPECTED_LEN * 0.8))
        self.assertLess(len(b), int(EXPECTED_LEN * 1.2))

        self.assertEqual(b"\x89PNG\r\n\x1a\n" +     # File header
                         b"\x00\x00\x00\rIHDR" +    # Header chunk header
                         b"\x00\x00\x02\x80" +      # Width 640
                         b"\x00\x00\x01\xe0",       # Height 480
                         b[:24])
