import os
import platform
import unittest

try:
    from android.os import Build
except ImportError:
    API_LEVEL = None
else:
    API_LEVEL = Build.VERSION.SDK_INT


class TestPsutil(unittest.TestCase):

    def test_disk(self):
        import psutil
        parts = psutil.disk_partitions(all=True)
        # See __ANDROID_API__ in patch. The native API was added in API level 21, so we
        # only support it on 64-bit, and doesn't work at runtime until API level 23.
        if API_LEVEL and (API_LEVEL < 23 or platform.architecture()[0] == "32bit"):
            self.assertFalse(parts)
        else:
            self.assertIn("/", [p.mountpoint for p in parts])

    def test_process(self):
        import getpass
        import psutil
        self.assertIn(os.getpid(), psutil.pids())
        p = psutil.Process(os.getpid())
        self.assertEqual(getpass.getuser(), p.username())
