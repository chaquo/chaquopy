import unittest


class TestSoundfile(unittest.TestCase):

    def test_basic(self):
        import io
        from os.path import dirname, join
        import numpy as np
        import soundfile

        def check_data(data, rate):
            self.assertEqual((17792, 2), data.shape)
            self.assertEqual(44100, rate)
            self.assertAlmostEqual(0.0112, np.mean(abs(data[:,0])), 4)

        data, rate = soundfile.read(join(dirname(__file__), "test.wav"))
        check_data(data, rate)
        for format, magic, size in [("WAV", b"RIFF", 71212),
                                    ("FLAC", b"fLaC", 14045),
                                    ("OGG", b"OggS", 9758)]:
            with self.subTest(format=format):
                f = io.BytesIO()
                soundfile.write(f, data, rate, format=format)
                b = f.getvalue()
                self.assertTrue(b.startswith(magic), b[:10])
                self.assertLess(abs(len(b) - size) / size, 0.1, len(b))

                f.seek(0)
                data, rate = soundfile.read(f)
                check_data(data, rate)
