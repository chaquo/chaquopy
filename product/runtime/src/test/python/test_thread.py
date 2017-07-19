from __future__ import absolute_import, division, print_function

from threading import Thread
from java import *
import unittest
from time import time, sleep

from com.chaquo.python import TestThread as JavaTestThread


class TestThread(unittest.TestCase):

    def test_gil_release_method(self):
        self.check_gil_release(JavaTestThread.BlockingMethods.blockStatic)
        self.check_gil_release(JavaTestThread.BlockingMethods().blockInstance)

    def test_gil_release_constructor(self):
        self.check_gil_release(JavaTestThread.BlockingConstructor)

    def check_gil_release(self, func):
        expected_delay = 0.1
        start = time()
        thread = Thread(target=self.split_sleep, args=[expected_delay])
        thread.start()
        func(int(expected_delay * 1000))
        thread.join()
        actual_delay = time() - start
        self.assertLess(abs(actual_delay - expected_delay), expected_delay * 0.15)

    def split_sleep(self, delay):
        for i in range(10):
            sleep(delay / 10)
