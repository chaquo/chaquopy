import unittest

class TestFFmpegPackage(unittest.TestCase):

    def test_input_output(self):
        import ffmpeg

        self.input_file = 'input.mp4'
        self.output_file = 'output.mp4'
        stream = ffmpeg.input(self.input_file).output(self.output_file)
        args = stream.get_args()
        expected_args = ['-i', self.input_file, self.output_file]
        self.assertEqual(args, expected_args)
