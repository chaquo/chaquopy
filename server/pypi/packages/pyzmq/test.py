from glob import glob
import os
from os.path import basename, dirname, isfile, islink, join
import platform
import unittest

try:
    from android.os import Build
    API_LEVEL = Build.VERSION.SDK_INT
except ImportError:
    API_LEVEL = None

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

    # See extract_so in importer.py.
    @unittest.skipUnless(API_LEVEL, "Android only")
    def test_importer(self):
        import zmq
        try:
            import h5py
        except ImportError:
            self.skipTest("requires h5py")

        h5py_mod = h5py.utils
        zmq_mod = zmq.backend.cython.utils

        def check_islink(mod, expected):
            file = mod.__file__
            self.assertEqual("utils.so", basename(file))
            self.assertTrue(isfile(file))
            self.assertFalse(islink(file))

            origin = mod.__spec__.origin
            if (platform.architecture()[0] == "64bit") and (API_LEVEL < 23):
                # See prepare_dlopen in importer.py. This test covers Python modules: for
                # non-Python libraries, see test_ctypes in test_android.py.
                self.assertNotIn("/", origin)
                origin = join(dirname(file), origin)
            else:
                self.assertRegex(origin, r"^/")

            link_paths = glob(file + ".*")
            if expected:
                self.assertEqual(1, len(link_paths))
                self.assertEqual(link_paths[0], origin)
                self.assertTrue(islink(origin))
                self.assertEqual(basename(file), os.readlink(origin))
            else:
                self.assertEqual(0, len(link_paths))
                self.assertEqual(file, origin)

        # The tests run in alphabetical order, so on devices which require symlinks, it should
        # be the zmq module which uses one.
        check_islink(h5py_mod, False)
        check_islink(zmq_mod, API_LEVEL < 23)
