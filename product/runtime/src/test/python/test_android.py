"""This file tests internal details of AndroidPlatform. These are not part of the public API
and should not be accessed by user code.
"""

from __future__ import absolute_import, division, print_function

from importlib import import_module
import sys
import unittest

from java.android.importer import AssetLoader

if sys.version_info[0] >= 3:
    from importlib import reload


REQS_PATH = "/android_asset/chaquopy/requirements.mp3"

try:
    from android.os import Build
    API_LEVEL = Build.VERSION.SDK_INT
except ImportError:
    API_LEVEL = None


@unittest.skipIf(API_LEVEL is None, "Not running on Android")
class TestAndroidImport(unittest.TestCase):

    def test_init(self):
        self.check_module("markupsafe", REQS_PATH + "/markupsafe/__init__.py",
                          package_path=[REQS_PATH],
                          source_head='# -*- coding: utf-8 -*-\n"""\n    markupsafe\n')

    def test_py(self):
        # Despite its name, this is a pure Python module.
        mod = self.check_module("markupsafe._native", REQS_PATH + "/markupsafe/_native.py",
                                source_head='# -*- coding: utf-8 -*-\n"""\n    markupsafe._native\n')

        delattr(mod, "escape")
        mod.hello = "world"
        reload(mod)
        self.assertTrue(hasattr(mod, "escape"))
        self.assertEqual("world", mod.hello)

    def test_so(self):
        mod = self.check_module("markupsafe._speedups", REQS_PATH + "/markupsafe/_speedups.so")

        with self.assertRaisesRegexp(ImportError,
                                     "'markupsafe._speedups': cannot reload a native module"):
            reload(mod)

    def check_module(self, mod_name, filename, package_path=None, source_head=None):
        sys.modules.pop(mod_name, None)
        mod = import_module(mod_name)
        self.assertEqual(mod_name, mod.__name__)
        self.assertEqual(filename, mod.__file__)
        if package_path:
            self.assertEqual(package_path, mod.__path__)
            self.assertEqual(mod_name, mod.__package__)
        else:
            self.assertFalse(hasattr(mod, "__path__"))
            self.assertEqual(mod_name.rpartition(".")[0], mod.__package__)
        loader = mod.__loader__
        self.assertIsInstance(loader, AssetLoader)

        data = loader.get_data(REQS_PATH + "/markupsafe/_constants.py")
        self.assertTrue(data.startswith(b'# -*- coding: utf-8 -*-\n"""\n    markupsafe._constants\n'),
                        data)
        with self.assertRaisesRegexp(IOError, "loader for '{}' can't access '/invalid.py'"
                                     .format(REQS_PATH)):
            loader.get_data("/invalid.py")
        with self.assertRaisesRegexp(IOError, "There is no item named 'invalid.py' in the archive"):
            loader.get_data(REQS_PATH + "/invalid.py")

        self.assertEqual(bool(package_path), loader.is_package(mod_name))
        self.assertIsNone(loader.get_code(mod_name))
        source = loader.get_source(mod_name)
        if source_head:
            self.assertTrue(source.startswith(source_head), source)
        else:
            self.assertIsNone(source)

        return mod

    def test_exception(self):
        pass
        # FIXME source code in traceback
        #
        # FIXME including if exception happened during import. SyntaxError is raised by compile
        # (which knows the filename), others can be raise by exec. Verify that neither is
        # supposed to raise an ImportError.
