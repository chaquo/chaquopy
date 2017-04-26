from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import unittest
from chaquopy.reflect import autoclass

class ReflectTest(unittest.TestCase):

    def test_stack(self):
        Stack = autoclass('java.util.Stack')
        StackSlash = autoclass('java/util/Stack')
        self.assertIs(Stack, StackSlash)
        stack = Stack()
        self.assertIsInstance(stack, Stack)
        stack.push('hello')
        stack.push('world')
        self.assertEqual(stack.pop(), 'world')
        self.assertEqual(stack.pop(), 'hello')
