import unittest
import sys


class TestZopeInterface(unittest.TestCase):

    def test_coptimizations(self):
        import zope.interface
        self.assertIn("zope.interface._zope_interface_coptimizations", sys.modules)

    def test_inside_function_call(self):
        from zope.interface.advice import getFrameInfo

        kind, module, f_locals, f_globals = getFrameInfo(sys._getframe())
        self.assertEqual(kind, "function call")
        self.assertTrue(f_locals is locals())
        for d in module.__dict__, f_globals:
            self.assertTrue(d is globals())

    def test_element(self):
        from zope.interface.interface import Element

        e1 = Element("foo")
        e2 = Element("bar")
        e1.setTaggedValue("x", 1)
        e2.setTaggedValue("x", 2)
        self.assertEqual(e1.getTaggedValue("x"), 1)
        self.assertEqual(e2.getTaggedValue("x"), 2)
