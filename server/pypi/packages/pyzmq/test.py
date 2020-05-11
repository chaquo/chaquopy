import unittest


ADDRESS = "tcp://127.0.0.1"
TIMEOUT = 500


class TestPyzmq(unittest.TestCase):

    def test_basic(self):
        import zmq
        ctx = zmq.Context()

        server = ctx.socket(zmq.PAIR)
        port = server.bind_to_random_port(ADDRESS)
        client = ctx.socket(zmq.PAIR)
        client.connect("{}:{}".format(ADDRESS, port))

        for msg_send in [b"hello", b"world"]:
            client.send(msg_send)
            server.poll(TIMEOUT)
            msg_recv = server.recv()
            self.assertEqual(msg_send, msg_recv)
