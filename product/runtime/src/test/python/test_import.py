from __future__ import absolute_import, division, print_function

import unittest
import sys

from java import *


class TestImport(unittest.TestCase):

    def no_module_error(self, module):
        return self.assertRaisesRegexp(ImportError, r"^No module named {}$".format(module))

    def no_name_error(self, name):
        return self.assertRaisesRegexp(ImportError, r"^cannot import name {}$".format(name))

    def test_enable(self):
        from java.lang import String
        set_import_enabled(False)
        with self.assertRaises(ImportError):
            from java.lang import String
        set_import_enabled(True)
        from java.lang import String

    def test_single(self):
        # "java" is different because there actually is a Python module by that name.
        from java.lang import String
        self.assertIs(String, jclass("java.lang.String"))
        self.assertNotIn("java.lang", sys.modules)

        from javax.xml import XMLConstants
        self.assertIs(XMLConstants, jclass("javax.xml.XMLConstants"))
        self.assertNotIn("javax", sys.modules)
        self.assertNotIn("javax.xml", sys.modules)

    def test_multiple(self):
        from java.lang import Integer, Float
        self.assertIs(Integer, jclass("java.lang.Integer"))
        self.assertIs(Float, jclass("java.lang.Float"))

        from java.lang import Integer, Integer
        self.assertIs(Integer, jclass("java.lang.Integer"))

    def test_errors(self):
        with self.no_module_error("lang.String"):
            import java.lang.String

        # "java" is different because there actually is a Python module by that name.
        with self.no_module_error("lang"):
            from java.lang import Nonexistent
        with self.no_module_error("lang"):
            from package1 import wildcard_java_lang

        with self.no_module_error("javax.xml"):
            from javax.xml import Nonexistent
        with self.no_module_error("javax.xml"):
            from package1 import wildcard_javax_xml

        with self.no_name_error("Nonexistent"):
            from java.lang import String, Nonexistent

        with self.assertRaisesRegexp(SyntaxError, "invalid syntax"):
            from package1 import syntax_error
        with self.no_name_error("nonexistent"):
            from package1 import recursive_import_error

    def test_package(self):
        # "java" is different because there actually is a Python module by that name.
        with self.no_module_error("lang"):
            import java.lang
        with self.no_name_error("lang"):
            from java import lang

        with self.no_module_error("javax.xml"):
            import javax.xml
        with self.no_module_error("javax"):
            from javax import xml

    def test_multi_language(self):
        from package1 import java, python
        self.assertEqual("java 1", java.x)
        self.assertEqual("python 1", python.x)
        import package1.python
        self.assertIs(python, package1.python)

        with self.assertRaisesRegexp(ImportError, r"^package1.both exists in both Java and Python. "
                                     "Access the Java copy with jclass\('package1.both'\), and the "
                                     "Python copy with 'import package1' followed by "
                                     "'package1.both'.$"):
            from package1 import both

        import package1
        self.assertEqual("both python 1", package1.both.x)

    def test_relative(self):
        # Error wording varies across Python versions.
        with self.assertRaisesRegexp(ValueError, (r"^[Aa]ttempted relative import (with no known "
                                                  r"parent package)|(in non-package)$")):
            from . import whatever

        from package1 import test_relative
        test_relative.run(self)

        from package1.package11 import test_relative
        test_relative.run(self)
