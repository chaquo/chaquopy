import importlib
from os.path import basename, isfile
import unittest

try:
    from android.os import Build
except ImportError:
    Build = None

ADDRESS = "tcp://127.0.0.1"
TIMEOUT = 500


class TestPyzmq(unittest.TestCase):

    def test_basic(self):
        import zmq

        with zmq.Context() as ctx:
            server = ctx.socket(zmq.PAIR)
            port = server.bind_to_random_port(ADDRESS)
            client = ctx.socket(zmq.PAIR)
            client.connect("{}:{}".format(ADDRESS, port))

            for msg_send in [b"hello", b"world"]:
                client.send(msg_send)
                server.poll(TIMEOUT)
                msg_recv = server.recv()
                self.assertEqual(msg_send, msg_recv)

            server.close()
            client.close()

    # Several packages have modules with the filename utils.so. Make sure the importer
    # handles that correctly.
    @unittest.skipUnless(Build, "Android only")
    def test_importer(self):
        import zmq
        zmq_mod = zmq.backend.cython.utils

        OTHER_MODULES = ["cytoolz.utils", "h5py.utils"]  # Alphabetical order.
        for name in OTHER_MODULES:
            try:
                other_mod = importlib.import_module(name)
                break
            except ImportError:
                pass
        else:
            self.skipTest(f"requires at least one of {OTHER_MODULES}")

        self.assertNotEqual(zmq_mod, other_mod)
        self.assertNotEqual(zmq_mod.__file__, other_mod.__file__)
        self.assertNotEqual(dir(zmq_mod), dir(other_mod))

        for mod in [zmq_mod, other_mod]:
            with self.subTest(mod):
                file = mod.__file__
                self.assertEqual("utils.so", basename(file))
                self.assertTrue(isfile(file))
