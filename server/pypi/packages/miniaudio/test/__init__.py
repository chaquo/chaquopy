from os.path import dirname, join
import unittest

class TestMiniaudio(unittest.TestCase):

    def test_mp3_info(self):
        import miniaudio

        sound = open(join(dirname(__file__), "sample.mp3"), "rb")
        info = miniaudio.mp3_get_info(sound)
        self.assertGreater(info.duration, 10.0)
        self.assertEqual(info.sample_format, miniaudio.SampleFormat.SIGNED16)
        self.assertEqual(info.nchannels, 2)
