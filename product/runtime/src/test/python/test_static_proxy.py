from __future__ import absolute_import, division, print_function

from unittest import TestCase

from java import *

class TestStaticProxy(TestCase):

    # Could happen if static proxies aren't regenerated correctly.
    def test_wrong_load_order(self):
        with self.assertRaisesRegexp(TypeError, "static_proxy class "
                                     "com.chaquo.python.static_proxy.WrongLoadOrder loaded "
                                     "before its Python counterpart"):
            from com.chaquo.python.static_proxy import WrongLoadOrder

    # Could happen if static proxies aren't regenerated correctly.
    def test_wrong_bases(self):
        with self.assertRaisesRegexp(TypeError, "expected extends java.lang.Object, but Java "
                                     "class actually extends java.lang.Exception"):
            class WrongExtends(static_proxy(package="com.chaquo.python.static_proxy")):
                pass

        with self.assertRaisesRegexp(TypeError, r"expected implements \['java.lang.Runnable', "
                                     r"'com.chaquo.python.StaticProxy'], but Java class actually "
                                     r"implements \[]"):
            from java.lang import Runnable
            class WrongImplements(static_proxy(None, Runnable,
                                               package="com.chaquo.python.static_proxy")):
                pass
