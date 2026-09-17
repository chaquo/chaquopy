import os
import unittest


class TestPsutil(unittest.TestCase):

    def test_disk(self):
        import psutil
        self.assertIn("/", [p.mountpoint for p in psutil.disk_partitions()])

    def test_process(self):
        import getpass
        import psutil
        self.assertIn(os.getpid(), psutil.pids())
        p = psutil.Process(os.getpid())
        self.assertEqual(getpass.getuser(), p.username())
