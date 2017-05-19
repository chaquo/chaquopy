from __future__ import absolute_import, division, print_function
import unittest
from chaquopy import autoclass, JavaException


class TestException(unittest.TestCase):

    def test_class_not_found(self):
        self.assertRaises(JavaException, autoclass, 'org.unknow.class')

    def test_java_exception_handling(self):
        Stack = autoclass('java.util.Stack')
        stack = Stack()
        try:
            stack.pop()
            self.fail("Expected exception to be thrown")
        except JavaException as je:
            # print "Got JavaException: " + str(je)
            # print "Got Exception Class: " + je.classname
            # print "Got stacktrace: \n" + '\n'.join(je.stacktrace)
            self.assertEquals("java.util.EmptyStackException", je.classname)

    def test_java_exception_chaining(self):
        Basics = autoclass('com.chaquo.python.Basics')
        basics = Basics()
        try:
            basics.methodExceptionChained()
            self.fail("Expected exception to be thrown")
        except JavaException as je:
            # print "Got JavaException: " + str(je)
            # print "Got Exception Class: " + je.classname
            # print "Got Exception Message: " + je.innermessage
            # print "Got stacktrace: \n" + '\n'.join(je.stacktrace)
            self.assertEquals("java.lang.IllegalArgumentException", je.classname)
            self.assertEquals("helloworld2", je.innermessage)
            self.assertIn("Caused by:", je.stacktrace)
            self.assertEquals(11, len(je.stacktrace))
