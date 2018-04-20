from __future__ import absolute_import, division, print_function

import unittest


class TestPyzmq(unittest.TestCase):

    def test_basic(self):
        import zmq
        self.assertGreater(zmq.Context().get(zmq.MAX_SOCKETS), 10)
