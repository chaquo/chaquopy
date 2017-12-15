"""This file tests internal details of AndroidPlatform. These are not part of the public API
and should not be accessed by user code.
"""

from __future__ import absolute_import, division, print_function

from contextlib import contextmanager
from importlib import import_module
import marshal
import os
from os.path import exists, join
import sys
from traceback import format_exc
import unittest

if sys.version_info[0] >= 3:
    from importlib import reload


REQS_ZIP = "requirements.mp3"
REQS_PATH = join("/android_asset/chaquopy", REQS_ZIP)

try:
    from android.os import Build  # noqa: F401
    from java.android import importer
    CACHE_ROOT = join(__loader__.finder.context.getCacheDir().toString(),  # noqa: F821
                      "chaquopy/AssetFinder", REQS_ZIP)
except ImportError:
    pass


@unittest.skipIf("Build" not in globals(), "Not running on Android")
class TestAndroidImport(unittest.TestCase):

    def test_init(self):
        self.check_module("markupsafe", REQS_PATH + "/markupsafe/__init__.py",
                          package_path=[REQS_PATH],
                          source_head='# -*- coding: utf-8 -*-\n"""\n    markupsafe\n')

    def test_py(self):
        # Despite its name, this is a pure Python module.
        mod_name = "markupsafe._native"
        filename = "markupsafe/_native.py"
        cache_filename = join(CACHE_ROOT, filename + "c")
        mod = self.check_module(
            mod_name, join(REQS_PATH, filename), cache_filename=cache_filename,
            source_head='# -*- coding: utf-8 -*-\n"""\n    markupsafe._native\n')

        mod.foo = 1
        delattr(mod, "escape")
        reload(mod)
        self.assertEqual(1, mod.foo)
        self.assertTrue(hasattr(mod, "escape"))

        # A valid .pyc should not be written again.
        with self.set_mode(cache_filename, "444"):
            mod = self.clean_reload(mod)

        # And if the header matches, the code in the .pyc should be used, whatever it is.
        header = self.read_pyc_header(cache_filename)
        with open(cache_filename, "wb") as pyc_file:
            pyc_file.write(header)
            code = compile("foo = 2", "<test>", "exec")
            marshal.dump(code, pyc_file)
        self.assertFalse(hasattr(mod, "foo"))  # Should have been removed by clean_reload.
        mod = self.clean_reload(mod)
        self.assertEqual(2, mod.foo)
        self.assertFalse(hasattr(mod, "escape"))

        # A .pyc with mismatching header should be written again.
        new_header = header[0:4] + b"\x00\x01\x02\x03" + header[8:]
        self.write_pyc_header(cache_filename, new_header)
        with self.set_mode(cache_filename, "444"):
            with self.assertRaisesRegexp(IOError, "Permission denied"):
                self.clean_reload(mod)
        self.clean_reload(mod)
        self.assertEqual(header, self.read_pyc_header(cache_filename))

    def read_pyc_header(self, filename):
        return open(filename, "rb").read(12)

    def write_pyc_header(self, filename, header):
        with open(filename, "r+b") as pyc_file:
            pyc_file.seek(0)
            pyc_file.write(header)

    def test_so(self):
        mod_name = "markupsafe._speedups"
        filename = "markupsafe/_speedups.{}.so".format(importer.abi)
        cache_filename = join(CACHE_ROOT, filename)
        mod = self.check_module(mod_name, join(REQS_PATH, filename), cache_filename=cache_filename)

        with self.assertRaisesRegexp(ImportError,
                                     "'{}': cannot reload a native module".format(mod_name)):
            reload(mod)

        # A valid file should not be extracted again.
        with self.set_mode(cache_filename, "444"):
            mod = self.clean_reload(mod)

        # A file with mismatching mtime should be extracted again.
        original_mtime = os.stat(cache_filename).st_mtime
        os.utime(cache_filename, None)
        with self.set_mode(cache_filename, "444"):
            with self.assertRaisesRegexp(IOError, "Permission denied"):
                self.clean_reload(mod)
        self.clean_reload(mod)
        self.assertEqual(original_mtime, os.stat(cache_filename).st_mtime)

    @contextmanager
    def set_mode(self, filename, mode_str):
        original_mode = os.stat(filename).st_mode
        try:
            os.chmod(filename, int(mode_str, 8))
            yield
        finally:
            os.chmod(filename, original_mode)

    def clean_reload(self, mod):
        sys.modules.pop(mod.__name__, None)
        new_mod = import_module(mod.__name__)
        self.assertIsNot(new_mod, mod)
        return new_mod

    def check_module(self, mod_name, filename, cache_filename=None, package_path=None,
                     source_head=None):
        if cache_filename:
            if exists(cache_filename):
                os.remove(cache_filename)
            sys.modules.pop(mod_name, None)  # Force reload, to check cache file is recreated.

        mod = import_module(mod_name)
        if cache_filename:
            self.assertTrue(exists(cache_filename))

        # Module attributes
        self.assertEqual(mod_name, mod.__name__)
        self.assertEqual(filename, mod.__file__)
        if package_path:
            self.assertEqual(package_path, mod.__path__)
            self.assertEqual(mod_name, mod.__package__)
        else:
            self.assertFalse(hasattr(mod, "__path__"))
            self.assertEqual(mod_name.rpartition(".")[0], mod.__package__)
        loader = mod.__loader__
        self.assertIsInstance(loader, importer.AssetLoader)

        # Optional loader methods
        data = loader.get_data(REQS_PATH + "/markupsafe/_constants.py")
        self.assertTrue(data.startswith(
            b'# -*- coding: utf-8 -*-\n"""\n    markupsafe._constants\n'), repr(data))
        with self.assertRaisesRegexp(IOError, "loader for '{}' can't access '/invalid.py'"
                                     .format(REQS_PATH)):
            loader.get_data("/invalid.py")
        with self.assertRaisesRegexp(IOError, "There is no item named 'invalid.py' in the archive"):
            loader.get_data(REQS_PATH + "/invalid.py")

        self.assertEqual(bool(package_path), loader.is_package(mod_name))
        self.assertIsNone(loader.get_code(mod_name))
        source = loader.get_source(mod_name)
        if source_head:
            self.assertTrue(source.startswith(source_head), repr(source))
        else:
            self.assertIsNone(source)
        self.assertEqual(filename, loader.get_filename(mod_name))

        return mod

    # Verify that the traceback builder can get source code from the loader in all contexts.
    # (The "package1" test files are also used in test_import.)
    def test_exception(self):
        # Compilation
        try:
            from package1 import syntax_error  # noqa
        except SyntaxError:
            s = format_exc()
            self.assertTrue(s.endswith(
                'File "/android_asset/chaquopy/app.mp3/package1/syntax_error.py", line 1\n'
                '    one two\n'
                '          ^\n'
                'SyntaxError: invalid syntax\n'), repr(s))
        else:
            self.fail()

        # Module execution
        try:
            from package1 import recursive_import_error  # noqa
        except ImportError:
            s = format_exc()
            self.assertRegexpMatches(
                s,
                r'File "/android_asset/chaquopy/app.mp3/package1/recursive_import_error.py", '
                r'line 1, in <module>\n'
                r'    from os import nonexistent\n'
                r"ImportError: cannot import name '?nonexistent'?\n$")
        else:
            self.fail()

        # After import complete
        class C(object):
            __html__ = None
        try:
            from markupsafe import _native
            _native.escape(C)
        except TypeError:
            s = format_exc()
            self.assertTrue(s.endswith(
                'File "/android_asset/chaquopy/requirements.mp3/markupsafe/_native.py", '
                'line 21, in escape\n'
                '    return s.__html__()\n'
                "TypeError: 'NoneType' object is not callable\n"), repr(s))
        else:
            self.fail()
