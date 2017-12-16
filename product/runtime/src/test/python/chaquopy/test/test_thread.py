from __future__ import absolute_import, division, print_function

from java import detach, jclass
from time import time, sleep
from threading import Thread
import sys

from .test_utils import FilterWarningsCase
from com.chaquo.python import TestThread as JavaTestThread
from java.lang import String

if sys.version_info[0] == 2:
    import thread as _thread
else:
    import _thread


class TestThread(FilterWarningsCase):

    def test_gil_release_method(self):
        self.check_gil_release(JavaTestThread.BlockingMethods.blockStatic)
        self.check_gil_release(JavaTestThread.BlockingMethods().blockInstance)

    def test_gil_release_constructor(self):
        self.check_gil_release(JavaTestThread.BlockingConstructor)

    def check_gil_release(self, blocking_func):
        self.assertFalse(JavaTestThread.blocked)
        delay = 0.1
        deadline = time() + (delay * 2)
        thread = Thread(target=blocking_func, args=[int(delay * 1000)])
        thread.start()
        while not JavaTestThread.blocked:   # Thread not started yet
            sleep(delay / 10)
            self.assertLess(time(), deadline)
        # If the GIL was not released, we'll never get to this point, because `blocked` is only
        # true while the Java function is actually executing.
        while JavaTestThread.blocked:       # Thread is sleeping
            sleep(delay / 10)
            self.assertLess(time(), deadline)
        thread.join()

    # The detach tests contain no assertions, but they will crash on Android if the detach
    # doesn't take place.
    def test_detach_manual(self):
        def run():
            String.valueOf(99)
            detach()
        _thread.start_new_thread(run, ())

    def test_detach_target(self):
        thread = Thread(target=lambda: String.valueOf(99))
        thread.start()
        thread.join()

    def test_detach_run(self):
        class MyThread(Thread):
            def run(self):
                String.valueOf(99)
        thread = MyThread()
        thread.start()
        thread.join()

    def test_detach_unattached(self):
        # This thread doesn't use any Java features, so should remain unattached.
        thread = Thread(target=lambda: None)
        thread.start()
        thread.join()

    def test_detach_python_exception(self):
        def run():
            raise Exception("Expected Python exception")
        thread = Thread(target=run)
        thread.start()
        thread.join()

    def test_detach_java_exception(self):
        def run():
            from java.lang import Integer
            Integer.parseInt("Expected Java exception")
        thread = Thread(target=run)
        thread.start()
        thread.join()

    # Test we don't run into ClassLoader issues looking up app classes from other threads.
    def test_app_class(self):
        result = []
        def run():
            result.append(jclass("com.chaquo.python.TestThreadAppClass"))
        thread = Thread(target=run)
        thread.start()
        thread.join()
        self.assertEqual("hello world", result[0].STR)
