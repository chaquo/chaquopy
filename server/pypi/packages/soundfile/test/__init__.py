import unittest


class TestSoundfile(unittest.TestCase):

    def test_basic(self):
        import io
        from os.path import dirname, join
        import soundfile

        data, rate = soundfile.read(join(dirname(__file__), "test.wav"))
        self.check_data(data, rate)
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
                self.check_data(data, rate)

    def check_data(self, data, rate):
        self.assertEqual((17792, 2), data.shape)
        self.assertEqual(44100, rate)
        self.assertAlmostEqual(0.14, max(data[:, 0]), 2)
