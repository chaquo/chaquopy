import unittest
import ffmpeg

class TestFFmpegPackage(unittest.TestCase):
    
    def test_ffmpeg_version(self):
        version = ffmpeg.get_ffmpeg_version()
        self.assertIsNotNone(version)
        self.assertIsInstance(version, str)
        self.assertTrue(len(version) > 0)
        
    def test_ffmpeg_formats(self):
        formats = ffmpeg.get_formats()
        self.assertIsNotNone(formats)
        self.assertIsInstance(formats, list)
        self.assertTrue(len(formats) > 0)
        
    def test_ffmpeg_codecs(self):
        codecs = ffmpeg.get_codecs()
        self.assertIsNotNone(codecs)
        self.assertIsInstance(codecs, list)
        self.assertTrue(len(codecs) > 0)

# if __name__ == '__main__':
#     unittest.main()
