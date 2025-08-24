import unittest

class TestPyLSL(unittest.TestCase):

    def test_pylsl(self):
        from pylsl import StreamOutlet
        self.assertEqual(type(StreamOutlet(name='myStream', type='EEG', channel_count=8)), "<class 'pylsl.pylsl.StreamInfo'>")