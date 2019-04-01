import os
import platform
import unittest


IS_ANDROID = ("ANDROID_DATA" in os.environ)
IS_64BIT = (platform.architecture()[0] == "64bit")


class TestPsutil(unittest.TestCase):

    def test_disk(self):
        import psutil
        parts = psutil.disk_partitions(all=True)
        if IS_ANDROID and not IS_64BIT:
            self.assertFalse(parts)
        else:
            self.assertIn("/", [p.mountpoint for p in parts])

    def test_network(self):
        import psutil
        addrs = psutil.net_if_addrs()
        if IS_ANDROID:
            self.assertFalse(addrs)
        else:
            self.assertIn("lo", addrs)

        self.assertIn("lo", psutil.net_if_stats())

    def test_process(self):
        import getpass
        import psutil
        self.assertIn(os.getpid(), psutil.pids())
        p = psutil.Process(os.getpid())
        self.assertEqual(getpass.getuser(), p.username())
