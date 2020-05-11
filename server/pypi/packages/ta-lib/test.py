import unittest


class TestTALib(unittest.TestCase):

    def test_basic(self):
        import numpy
        import talib
        data = numpy.asarray([1.0, 2.0, 3.0, 4.0])
        sma = talib.SMA(data, timeperiod=2)
        self.assertEqual([1.5, 2.5, 3.5], list(sma)[1:])
