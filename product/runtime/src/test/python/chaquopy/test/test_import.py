from __future__ import absolute_import, division, print_function

from java import jclass, set_import_enabled
import sys

from .test_utils import FilterWarningsCase


class TestImport(FilterWarningsCase):

    def no_module_error(self, module):
        return self.assertRaisesRegexp(ImportError, r"^No module named '?{}'?$".format(module))

    def no_name_error(self, name):
        return self.assertRaisesRegexp(ImportError, r"^cannot import name '?{}'?$".format(name))

    def test_enable(self):
        # Should be enabled by default
        from java.lang import String  # noqa: F401

        set_import_enabled(False)
        with self.assertRaises(ImportError):
            from java.lang import String  # noqa: F811
        set_import_enabled(True)
        from java.lang import String  # noqa: F401, F811

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
        # "java" sub-packages give different errors on Python 2.7 because there actually is a
        # Python module by that name.
        with self.no_module_error(r"(java.lang|lang.String)"):
            import java.lang.String  # noqa: F401
        with self.no_module_error(r"(java.)?lang"):
            from java.lang import Nonexistent  # noqa: F401
        with self.no_module_error(r"(java.)?lang"):
            from package1 import wildcard_java_lang  # noqa: F401

        with self.no_module_error(r"javax(.xml)?"):
            from javax.xml import Nonexistent  # noqa: F401, F811
        with self.no_module_error(r"javax(.xml)?"):
            from package1 import wildcard_javax_xml  # noqa: F401

        # A Java name and a nonexistent one.
        with self.no_name_error("Nonexistent"):
            from java.lang import String, Nonexistent  # noqa: F401, F811

        # A Python name and a nonexistent one.
        with self.no_name_error("Nonexistent"):
            from sys import path, Nonexistent  # noqa: F401, F811

        # These test files are also used in test_android.py.
        with self.assertRaisesRegexp(SyntaxError, "invalid syntax"):
            from package1 import syntax_error  # noqa: F401
        with self.no_name_error("nonexistent"):
            from package1 import recursive_import_error  # noqa: F401

    def test_package(self):
        # See note above about "java" sub-packages.
        with self.no_module_error(r"(java.)?lang"):
            import java.lang  # noqa: F401
        with self.no_name_error(r"(java.)?lang"):
            from java import lang  # noqa: F401

        with self.no_module_error(r"javax(.xml)?"):
            import javax.xml  # noqa: F401
        with self.no_module_error("javax"):
            from javax import xml  # noqa: F401

    def test_multi_language(self):
        from package1 import java, python, both
        self.assertEqual("java 1", java.x)
        self.assertEqual("python 1", python.x)
        self.assertEqual("both python 1", both.x)
        self.assertEqual("both java 1", jclass("package1.both").x)

        import package1.python
        import package1.both
        self.assertIs(python, package1.python)
        self.assertIs(both, package1.both)

        # A name from each language, and a nonexistent one.
        with self.no_name_error("Nonexistent"):
            from package1 import java, Nonexistent, python  # noqa: F401, F811

    def test_relative(self):
        # Error wording varies across Python versions.
        from module1 import test_relative
        test_relative(self)
        from package1 import test_relative
        test_relative(self)
        from package1.package11 import test_relative
        test_relative(self)

    def test_namespace(self):
        from namespace import mod1
        self.assertEqual("Module within an implicit namespace package", mod1.x)
