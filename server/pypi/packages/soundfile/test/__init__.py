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

    # Most users of soundfile are only installing it as a requirement of librosa, so do a basic
    # test of that.
    def test_librosa(self):
        from os.path import dirname, join
        import librosa
        from librosa.util import normalize

        data, rate = librosa.load(join(dirname(__file__), "test.wav"), sr=None, mono=False)
        self.check_data(data.T, rate)
        data_norm = normalize(data, axis=1)
        self.assertAlmostEqual(1, max(data_norm[0]))

    def check_data(self, data, rate):
        self.assertEqual((17792, 2), data.shape)
        self.assertEqual(44100, rate)
        self.assertAlmostEqual(0.14, max(data[:,0]), 2)
