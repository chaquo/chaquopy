import os
from os.path import dirname, exists, join, realpath
import subprocess
import sys
from warnings import catch_warnings, filterwarnings

from android.os import Build

from ..test_utils import FilterWarningsCase
from . import ABI, context


class TestAndroidStdlib(FilterWarningsCase):

    # For ctypes, see test_import.py.

    def test_datetime(self):
        import datetime
        # This is the interface to the native _datetime module, which is required by NumPy. The
        # attribute will only exist if _datetime was available when datetime was first
        # imported.
        self.assertTrue(datetime.datetime_CAPI)

    def test_hashlib(self):
        import hashlib
        INPUT = b"The quick brown fox jumps over the lazy dog"
        TESTS = [
            # OpenSSL and built-in, OpenSSL preferred.
            ("sha1", "2fd4e1c67a2d28fced849ee1bb76e7391b93eb12"),

            # OpenSSL and built-in, built-in preferred.
            ("blake2b", ("a8add4bdddfd93e4877d2746e62817b116364a1fa7bc148d95090bc7333b3673f8240"
                         "1cf7aa2e4cb1ecd90296e3f14cb5413f8ed77be73045b13914cdcd6a918")),

            # OpenSSL only.
            ("sm3", "5fdfe814b8573ca021983970fc79b2218c9570369b4859684e2e4c3fc76cb8ea"),
        ]
        for name, expected in TESTS:
            with self.subTest(algorithm=name):
                # With initial data
                self.assertEqual(expected, hashlib.new(name, INPUT).hexdigest())
                # Without initial data
                h = hashlib.new(name)
                h.update(INPUT)
                self.assertEqual(expected, h.hexdigest())

                if name in hashlib.algorithms_guaranteed:
                    # With initial data
                    self.assertEqual(expected, getattr(hashlib, name)(INPUT).hexdigest())
                    # Without initial data
                    h = getattr(hashlib, name)()
                    h.update(INPUT)
                    self.assertEqual(expected, h.hexdigest())
                else:
                    self.assertFalse(hasattr(hashlib, name))

    def test_json(self):
        from json import encoder, scanner
        # These attributes will be None if the native _json module was unavailable when json
        # was first imported, which would significantly reduce the module's performance.
        self.assertTrue(encoder.c_make_encoder)
        self.assertTrue(scanner.c_make_scanner)

    def test_lib2to3(self):
        with catch_warnings():
            for category in [DeprecationWarning, PendingDeprecationWarning]:
                filterwarnings("default", category=category)

            # Requires grammar files to be available in stdlib zip.
            from lib2to3 import pygram  # noqa: F401

    def test_locale(self):
        import locale
        self.assertEqual("UTF-8", locale.getlocale()[1])
        with catch_warnings():
            filterwarnings("default", category=DeprecationWarning)
            self.assertEqual("UTF-8", locale.getdefaultlocale()[1])
        self.assertEqual("utf-8",  # Became lower-case in Python 3.11.
                         locale.getpreferredencoding().lower())
        self.assertEqual("utf-8", sys.getdefaultencoding())
        self.assertEqual("utf-8", sys.getfilesystemencoding())

    def test_multiprocessing(self):
        from multiprocessing.dummy import Pool
        import random
        import time

        def square_slowly(x):
            time.sleep(random.uniform(0.1, 0.2))
            return x ** 2

        with Pool(8) as pool:
            start = time.time()
            self.assertEqual([0, 1, 4, 9, 16, 25, 36, 49],
                             pool.map(square_slowly, range(8), chunksize=1))
            duration = time.time() - start
            self.assertGreater(duration, 0.1)
            self.assertLess(duration, 0.25)

        from multiprocessing import get_context, synchronize
        ctx = get_context()
        for name in ["Barrier", "BoundedSemaphore", "Condition", "Event", "Lock", "RLock",
                     "Semaphore"]:
            cls = getattr(synchronize, name)
            with self.assertRaisesRegex(OSError, "This platform lacks a functioning sem_open"):
                if name == "Barrier":
                    cls(1, ctx=ctx)
                else:
                    cls(ctx=ctx)

    def test_os(self):
        self.assertEqual("posix", os.name)
        self.assertTrue(os.access(os.environ["HOME"], os.R_OK | os.W_OK | os.X_OK))

        self.assertTrue(os.get_exec_path())
        for name in os.get_exec_path():
            with self.subTest(name=name):
                self.assertTrue(os.access(name, os.X_OK))

        for args in [[], [1]]:
            with self.assertRaisesRegex(
                OSError, r"Inappropriate ioctl for device|Not a typewriter"
            ):
                os.get_terminal_size(*args)

    def test_pickle(self):
        import pickle
        # This attribute will only exist if the native _pickle module was available when
        # pickle was first imported.
        self.assertTrue(pickle.PickleBuffer)

    def test_platform(self):
        import platform

        python_bits = platform.architecture()[0]
        self.assertEqual(python_bits, "64bit" if ("64" in Build.CPU_ABI) else "32bit")

        # Requires sys.executable to exist.
        p = platform.platform()
        self.assertRegex(p, r"^Linux")

    def test_select(self):
        import select
        self.assertFalse(hasattr(select, "kevent"))
        self.assertFalse(hasattr(select, "kqueue"))

        import selectors
        self.assertIs(selectors.DefaultSelector, selectors.EpollSelector)

    def test_signal(self):
        import enum
        import signal

        # These functions may be unavailable if _signal was compiled incorrectly.
        for name in ["pthread_sigmask", "sigpending", "sigwait", "valid_signals"]:
            with self.subTest(name=name):
                self.assertTrue(hasattr(signal, name))

        vs = signal.valid_signals()
        self.assertIsInstance(vs, set)
        vs = list(vs)

        self.assertEqual(1, vs[0])
        self.assertIs(signal.SIGHUP, vs[0])
        self.assertIsInstance(vs[0], signal.Signals)
        self.assertIsInstance(vs[0], enum.IntEnum)
        self.assertEqual("<Signals.SIGHUP: 1>", repr(vs[0]))

    def test_socket(self):
        import socket
        for name in ["if_nameindex", "if_nametoindex", "if_indextoname"]:
            for args in [[], ["whatever"]]:
                with self.assertRaisesRegex(
                    OSError, "this function is not available in this build of Python"
                ):
                    getattr(socket, name)(*args)

    def test_sqlite(self):
        import sqlite3
        conn = sqlite3.connect(":memory:")
        conn.execute("create table test (a text, b text)")
        conn.execute("insert into test values ('alpha', 'one'), ('bravo', 'two')")
        cur = conn.execute("select b from test where a = 'bravo'")
        self.assertEqual([("two",)], cur.fetchall())

    def test_ssl(self):
        from urllib.request import urlopen
        resp = urlopen("https://chaquo.com/chaquopy/")
        self.assertEqual(200, resp.getcode())
        self.assertRegex(resp.info()["Content-type"], r"^text/html")

    def test_subprocess(self):
        # An executable on the PATH.
        subprocess.run(["ls", os.environ["HOME"]])

        # A nonexistent executable.
        for name in ["nonexistent",                 # PATH search
                     "/system/bin/nonexistent"]:    # Absolute filename
            with self.subTest(name=name), self.assertRaises(FileNotFoundError):
                subprocess.run([name])

    def test_sys(self):
        self.assertEqual("", sys.abiflags)
        self.assertEqual([""], sys.argv)
        self.assertTrue(exists(sys.executable), sys.executable)

        # See "ac_cv_aligned_required" in target/python/build.sh.
        self.assertEqual("siphash24" if (sys.version_info < (3, 11)) else "siphash13",
                         sys.hash_info.algorithm)

        chaquopy_dir = f"{context.getFilesDir()}/chaquopy"
        self.assertEqual(
            [join(realpath(chaquopy_dir), path) for path in
             ["AssetFinder/app", "AssetFinder/requirements", f"AssetFinder/stdlib-{ABI}"]] +
            [join(chaquopy_dir, path) for path in
             ["stdlib-common.imy", "bootstrap.imy", f"bootstrap-native/{ABI}"]],
            sys.path)
        for p in sys.path:
            self.assertTrue(exists(p), p)

        self.assertRegex(sys.platform, r"^linux")
        self.assertNotIn("dirty", sys.version)

    def test_sysconfig(self):
        import sysconfig
        ldlibrary = "libpython{}.{}.so".format(*sys.version_info[:2])
        self.assertEqual(ldlibrary, sysconfig.get_config_vars()["LDLIBRARY"])

        if sys.version_info < (3, 12):
            with catch_warnings():
                filterwarnings("default", category=DeprecationWarning)
                import distutils.sysconfig
            self.assertEqual(ldlibrary, distutils.sysconfig.get_config_vars()["LDLIBRARY"])

    def test_tempfile(self):
        import tempfile
        expected_dir = join(str(context.getCacheDir()), "chaquopy/tmp")
        self.assertEqual(expected_dir, tempfile.gettempdir())
        with tempfile.NamedTemporaryFile() as f:
            self.assertEqual(expected_dir, dirname(f.name))

    def test_time(self):
        import time
        t = time.gmtime(1582917965)
        self.assertEqual("Fri, 28 Feb 2020 19:26:05",
                         time.strftime("%a, %d %b %Y %H:%M:%S", t))

    def test_warnings(self):
        import warnings
        # The default "ignore" filters should have been removed. And despite what the
        # documentation says, the unit test framework inserts its filters not in the
        # TextTestRunner, but in unittest.main, which we're not using. So the only active
        # filter should be the one inserted by FilterWarningsCase.
        self.assertEqual([("error", None, Warning, None, 0)], warnings.filters)
