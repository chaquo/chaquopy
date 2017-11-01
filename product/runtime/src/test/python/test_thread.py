from __future__ import absolute_import, division, print_function

from java import *
import unittest
from time import time, sleep
from threading import Thread
import sys

if sys.version_info[0] == 2:
    import thread as _thread
else:
    import _thread

from com.chaquo.python import TestThread as JavaTestThread
from java.lang import String


class TestThread(unittest.TestCase):

    def test_gil_release_method(self):
        self.check_gil_release(JavaTestThread.BlockingMethods.blockStatic)
        self.check_gil_release(JavaTestThread.BlockingMethods().blockInstance)

    def test_gil_release_constructor(self):
        self.check_gil_release(JavaTestThread.BlockingConstructor)

    def check_gil_release(self, blocking_func):
        self.assertFalse(JavaTestThread.blocked)
        delay = 0.1
        deadline = time() + delay*2
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
    def test_detach(self):
        def run():
            String.valueOf(99)
            detach()
        _thread.start_new_thread(run, ())

    def test_threading_target(self):
        thread = Thread(target=lambda: String.valueOf(99))
        thread.start()
        thread.join()

    def test_threading_run(self):
        class MyThread(Thread):
            def run(self):
                String.valueOf(99)
        thread = MyThread()
        thread.start()
        thread.join()

    # Test automatic detaching with an unattached thread.
    def test_threading_unattached(self):
        thread = Thread(target=lambda: None)
        thread.start()
        thread.join()
