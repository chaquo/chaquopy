from contextlib import contextmanager
import ctypes.util
import queue
import re
import subprocess
import sys
from threading import Thread
from time import time

from android.util import Log

from ..test_utils import API_LEVEL, FilterWarningsCase


redirected_native = False


class TestAndroidOutput(FilterWarningsCase):

    maxDiff = None

    def setUp(self):
        self.logcat_process = subprocess.Popen(
            ["logcat", "-v", "tag"], stdout=subprocess.PIPE, errors="backslashreplace"
        )
        self.logcat_queue = queue.Queue()

        def logcat_thread():
            for line in self.logcat_process.stdout:
                self.logcat_queue.put(line.rstrip("\n"))
            self.logcat_process.stdout.close()
        Thread(target=logcat_thread).start()

        tag, start_marker = "python.test", f"{self.id()} {time()}"
        Log.i(tag, start_marker)
        self.assert_log("I", tag, start_marker, skip=True, timeout=5)

    def assert_logs(self, level, tag, expected, **kwargs):
        for line in expected:
            self.assert_log(level, tag, line, **kwargs)

    def assert_log(self, level, tag, expected, *, skip=False, timeout=0.5):
        deadline = time() + timeout
        while True:
            try:
                line = self.logcat_queue.get(timeout=(deadline - time()))
            except queue.Empty:
                self.fail(f"line not found: {expected!r}")
            if match := re.fullmatch(fr"(.)/{tag}: (.*)", line):
                try:
                    self.assertEqual(level, match[1])
                    self.assertEqual(expected, match[2])
                    break
                except AssertionError:
                    if not skip:
                        raise

    def tearDown(self):
        self.logcat_process.terminate()
        self.logcat_process.wait(0.1)

    @contextmanager
    def unbuffered(self, stream):
        stream.reconfigure(write_through=True)
        try:
            yield
        finally:
            stream.reconfigure(write_through=False)

    def test_str(self):
        for stream_name, level in [("stdout", "I"), ("stderr", "W")]:
            with self.subTest(stream=stream_name):
                stream = getattr(sys, stream_name)
                # We use assertIn rather than assertEqual, because the demo app wraps the
                # TextLogStream with a ConsoleOutputStream.
                tag = f"python.{stream_name}"
                self.assertIn(f"<TextLogStream '{tag}'>", repr(stream))

                self.assertTrue(stream.writable())
                self.assertFalse(stream.readable())
                self.assertEqual("UTF-8", stream.encoding)
                self.assertEqual("backslashreplace", stream.errors)
                self.assertTrue(stream.line_buffering)
                self.assertFalse(stream.write_through)

                def write(s, lines=None):
                    self.assertEqual(len(s), stream.write(s))
                    if lines is None:
                        lines = [s]
                    self.assert_logs(level, tag, lines)

                # Single-line messages,
                with self.unbuffered(stream):
                    write("", [])

                    write("a")
                    write("Hello")
                    write("Hello world")
                    write(" ")
                    write("  ")

                    # Non-ASCII text
                    write("ol\u00e9")  # Spanish
                    write("\u4e2d\u6587")  # Chinese

                    # Non-BMP emoji
                    write("\U0001f600")

                    # Null characters are logged using "modified UTF-8".
                    write("\u0000", [r"\xc0\x80"])
                    write("a\u0000", [r"a\xc0\x80"])
                    write("\u0000b", [r"\xc0\x80b"])
                    write("a\u0000b", [r"a\xc0\x80b"])

                # Multi-line messages. Avoid identical consecutive lines, as they may
                # activate "chatty" filtering and break the tests.
                write("\nx", [""])
                write("\na\n", ["x", "a"])
                write("\n", [""])
                write("b\n", ["b"])
                write("c\n\n", ["c", ""])
                write("d\ne", ["d"])
                write("xx", [])
                write("f\n\ng", ["exxf", ""])
                write("\n", ["g"])

                with self.unbuffered(stream):
                    write("\nx", ["", "x"])
                    write("\na\n", ["", "a"])
                    write("\n", [""])
                    write("b\n", ["b"])
                    write("c\n\n", ["c", ""])
                    write("d\ne", ["d", "e"])
                    write("xx", ["xx"])
                    write("f\n\ng", ["f", "", "g"])
                    write("\n", [""])

                # "\r\n" should be translated into "\n".
                write("hello\r\n", ["hello"])
                write("hello\r\nworld\r\n", ["hello", "world"])
                write("\r\n", [""])

                for obj in [b"", b"hello", None, 42]:
                    with self.subTest(obj=obj):
                        with self.assertRaisesRegex(TypeError, fr"write\(\) argument must be "
                                                    fr"str, not {type(obj).__name__}"):
                            stream.write(obj)

                # Manual flushing is supported.
                write("hello", [])
                stream.flush()
                self.assert_log(level, tag, "hello")
                write("hello", [])
                write("world", [])
                stream.flush()
                self.assert_log(level, tag, "helloworld")

                # Long lines are split into blocks of 1000 *characters*, but TextIOWrapper
                # should then join them back together as much as possible without
                # exceeding 4000 UTF-8 *bytes*.
                #
                # ASCII (1 byte per character)
                write(("foobar" * 700) + "\n",
                      [("foobar" * 666) + "foob",  # 4000 bytes
                       "ar" + ("foobar" * 33)])  # 200 bytes

                # "Full-width" digits 0-9 (3 bytes per character)
                s = "\uff10\uff11\uff12\uff13\uff14\uff15\uff16\uff17\uff18\uff19"
                write((s * 150) + "\n",
                      [s * 100,  # 3000 bytes
                       s * 50])  # 1500 bytes

                s = "0123456789"
                write(s * 200, [])
                write(s * 150, [])
                write(s * 51, [s * 350])  # 3500 bytes
                write("\n", [s * 51])  # 510 bytes

    def test_bytes(self):
        for stream_name, level in [("stdout", "I"), ("stderr", "W")]:
            with self.subTest(stream=stream_name):
                stream = getattr(sys, stream_name).buffer
                tag = f"python.{stream_name}"
                self.assertEqual(f"<BinaryLogStream '{tag}'>", repr(stream))
                self.assertTrue(stream.writable())
                self.assertFalse(stream.readable())

                def write(b, lines=None):
                    self.assertEqual(len(b), stream.write(b))
                    if lines is None:
                        lines = [b.decode()]
                    self.assert_logs(level, tag, lines)

                # Single-line messages,
                write(b"", [])

                write(b"a")
                write(b"Hello")
                write(b"Hello world")
                write(b" ")
                write(b"  ")

                # Non-ASCII text
                write(b"ol\xc3\xa9")  # Spanish
                write(b"\xe4\xb8\xad\xe6\x96\x87")  # Chinese

                # Non-BMP emoji
                write(b"\xf0\x9f\x98\x80")

                # Null characters are logged using "modified UTF-8".
                write(b"\x00", [r"\xc0\x80"])
                write(b"a\x00", [r"a\xc0\x80"])
                write(b"\x00b", [r"\xc0\x80b"])
                write(b"a\x00b", [r"a\xc0\x80b"])

                # Invalid UTF-8
                write(b"\xff", [r"\xff"])
                write(b"a\xff", [r"a\xff"])
                write(b"\xffb", [r"\xffb"])
                write(b"a\xffb", [r"a\xffb"])

                # Log entries containing newlines are shown differently by `logcat -v
                # tag`, `logcat -v long`, and Android Studio. We currently use `logcat -v
                # tag`, which shows each line as if it was a separate log entry, but
                # strips a single trailing newline.
                #
                # On newer versions of Android, all three of the above tools (or maybe
                # Logcat itself) will also strip any number of leading newlines.
                write(b"\nx", ["", "x"] if API_LEVEL < 30 else ["x"])
                write(b"\na\n", ["", "a"] if API_LEVEL < 30 else ["a"])
                write(b"\n", [""])
                write(b"b\n", ["b"])
                write(b"c\n\n", ["c", ""])
                write(b"d\ne", ["d", "e"])
                write(b"xx", ["xx"])
                write(b"f\n\ng", ["f", "", "g"])
                write(b"\n", [""])

                # "\r\n" should be translated into "\n".
                write(b"hello\r\n", ["hello"])
                write(b"hello\r\nworld\r\n", ["hello", "world"])
                write(b"\r\n", [""])

                for obj in ["", "hello", None, 42]:
                    with self.subTest(obj=obj):
                        if isinstance(obj, str):
                            message = r"decoding str is not supported"
                        else:
                            message = (fr"decoding to str: need a bytes-like object, "
                                       fr"{type(obj).__name__} found")
                        with self.assertRaisesRegex(TypeError, message):
                            stream.write(obj)

    def test_native(self):
        c_write = ctypes.CDLL(ctypes.util.find_library("c")).write
        streams = [("native.stdout", "I", 1), ("native.stderr", "W", 2)]

        def write(b, lines=None):
            self.assertIsInstance(b, bytes)
            self.assertEqual(len(b), c_write(fileno, b, len(b)))
            if lines is None:
                lines = [b.decode()]
            self.assert_logs(level, tag, lines)

        # By default, the native streams are not redirected, so everything written to them
        # will be lost. Because there's no way to undo the redirection, we can only test
        # this mode once per process.
        global redirected_native
        if redirected_native:
            print("Can't re-run non-redirected tests")
        else:
            print("Running non-redirected tests")
            for tag, level, fileno in streams:
                with self.subTest(tag=tag):
                    # Add begin and end markers to make sure these writes don't get mixed
                    # up with the redirected writes below.
                    for b in [
                        b"BEGIN non-redirected tests",
                        b"", b"a", b"Hello", b"Hello world", b"Hello world\n",
                        b"END non-redirected tests"
                    ]:
                        with self.subTest(b=b):
                            write(b, [])

        from com.chaquo.python import Python
        Python.getPlatform().redirectStdioToLogcat()
        redirected_native = True

        for tag, level, fileno in streams:
            with self.subTest(tag=tag):
                write(b"", [])
                write(b"a")
                write(b"Hello")
                write(b"Hello world")

                # See above comment: "Log entries containing newlines..."
                write(b"\n", [""])
                write(b"Hello world\n", ["Hello world"])
                write(b"Hello\nworld", ["Hello", "world"])
                write(b"Hello\nworld\n", ["Hello", "world"])


class TestAndroidInput(FilterWarningsCase):

    def test_str(self):
        self.assertTrue(sys.stdin.readable())
        self.assertFalse(sys.stdin.writable())
        self.assertEqual("", sys.stdin.read())
        self.assertEqual("", sys.stdin.read(42))
        self.assertEqual("", sys.stdin.readline())
        self.assertEqual("", sys.stdin.readline(42))
