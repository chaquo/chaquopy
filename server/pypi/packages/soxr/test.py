import unittest

class TestSoxr(unittest.TestCase):

    def test_basic(self):
        import soxr

        inputSamplerate = 48000
        targetSamplerate = 16000
        
        x = [1.0] * inputSamplerate
        y = soxr.resample(
            x,          # 1D(mono) or 2D(frames, channels) array input
            inputSamplerate,      # input samplerate
            targetSamplerate       # target samplerate
        )
        self.assertEqual(y.size, targetSamplerate)
