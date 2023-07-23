from os.path import dirname, join
import unittest

class TestMiniaudio(unittest.TestCase):

    def test_mp3(self):
        import miniaudio

        info = miniaudio.mp3_get_file_info(join(dirname(__file__), "sample.mp3"))
        self.assertAlmostEqual(info.duration, 10.1093878)
        self.assertEqual(info.sample_format, miniaudio.SampleFormat.SIGNED16)
        self.assertEqual(info.nchannels, 2)
