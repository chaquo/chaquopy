import unittest


class TestLameenc(unittest.TestCase):

    # https://github.com/chrisstaite/lameenc/blob/master/README.md
    def test_basic(self):
        import lameenc
        import os

        BIT_RATE = 128
        SAMPLE_RATE = 16000
        CHANNELS = 2
        BITS_PER_SAMPLE = 16

        encoder = lameenc.Encoder()
        encoder.set_bit_rate(BIT_RATE)
        encoder.set_in_sample_rate(SAMPLE_RATE)
        encoder.set_channels(CHANNELS)
        encoder.set_quality(2)  # 2-highest, 7-fastest

        # Generate 1 second of noise
        pcm = os.urandom(SAMPLE_RATE * CHANNELS * BITS_PER_SAMPLE // 8)

        mp3_data = encoder.encode(pcm)
        mp3_data += encoder.flush()

        # Header starts at a byte boundary with an 11-bit sync word, which is all 1s.
        self.assertEqual(mp3_data[0], 0xff)
        self.assertIn(mp3_data[1] & 0xf0, [0xe0, 0xf0])

        # Length should be approximately equal to bit rate.
        byte_rate = BIT_RATE * 1000 // 8
        self.assertGreater(len(mp3_data), byte_rate * 0.75)
        self.assertLess(len(mp3_data), byte_rate * 1.25)
