from __future__ import absolute_import, division, print_function

import unittest


class TestObspy(unittest.TestCase):

    # Not a very popular package, so just check we can import it and that its ctypes
    # functionality works correctly.
    def test_basic(self):
        from obspy.signal import headers
        headers.clibsignal.calcSteer  # Will cause an exception if undefined.
