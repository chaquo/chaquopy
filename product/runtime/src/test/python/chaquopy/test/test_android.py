"""This file tests internal details of AndroidPlatform. These are not part of the public API,
and should not be accessed or relied upon by user code.
"""

from __future__ import absolute_import, division, print_function

from contextlib import contextmanager
import imp
from importlib import import_module, reload
from importlib.util import cache_from_source, MAGIC_NUMBER
import marshal
import os
from os.path import dirname, exists, join
import pkgutil
import platform
import shlex
from subprocess import check_output
import sys
from traceback import format_exc
import types
import unittest


try:
    from android.os import Build
except ImportError:
    API_LEVEL = None
else:
    API_LEVEL = Build.VERSION.SDK_INT
    from java.android import importer
    context = __loader__.finder.context  # noqa: F821

    from com.chaquo.python.android import AndroidPlatform
    APP_ZIP = "app.zip"
    REQS_COMMON_ZIP = "requirements-common.zip"
    REQS_ABI_ZIP = "requirements-{}.zip".format(AndroidPlatform.ABI)
    multi_abi = len([name for name in context.getAssets().list("chaquopy")
                     if name.startswith("requirements")]) > 2

def setUpModule():
    if API_LEVEL is None:
        raise unittest.SkipTest("Not running on Android")


class TestAndroidPlatform(unittest.TestCase):

    # 64-bit should be preferred on devices which support it. We use Build.SUPPORTED_ABIS to
    # detect support because Build.CPU_ABI always returns the active ABI of the app, which can
    # be 32-bit even on a 64-bit device (https://stackoverflow.com/a/53158339).
    #
    # This test will only pass on a 64-bit device if the 64-bit ABI was included in abiFilters.
    @unittest.skipUnless(API_LEVEL and API_LEVEL >= 21, "Requires Build.SUPPORTED_ABIS")
    def test_abi(self):
        python_bits = platform.architecture()[0]
        self.assertEqual(python_bits,
                         "64bit" if set(Build.SUPPORTED_ABIS) & set(["arm64-v8a", "x86_64"])
                         else "32bit")


class TestAndroidImport(unittest.TestCase):

    def test_init(self):
        self.check_py("markupsafe", REQS_COMMON_ZIP, "markupsafe/__init__.py", "escape",
                      is_package=True)
        self.check_py("package1", APP_ZIP, "package1/__init__.py", "test_relative",
                      is_package=True,
                      source_head="# This package is used by chaquopy.test.test_android.")

    def test_py(self):
        self.check_py("markupsafe._native", REQS_COMMON_ZIP, "markupsafe/_native.py", "escape")
        self.check_py("package1.package11.python", APP_ZIP, "package1/package11/python.py",
                      "x", source_head='x = "python 11"')

    def check_py(self, mod_name, zip_name, zip_path, existing_attr, **kwargs):
        filename = asset_path(zip_name, zip_path)
        # In build.gradle, .pyc pre-compilation is enabled for everything except app.zip.
        cache_filename = cache_from_source(filename) if (zip_name == APP_ZIP) else None
        mod = self.check_module(mod_name, filename, cache_filename, **kwargs)
        self.assertNotPredicate(exists, filename)
        if cache_filename is None:
            self.assertNotPredicate(exists, cache_from_source(filename))

        new_attr = "check_py_attr"
        self.assertFalse(hasattr(mod, new_attr))
        setattr(mod, new_attr, 1)
        delattr(mod, existing_attr)
        reload(mod)  # Should reuse existing module object.
        self.assertEqual(1, getattr(mod, new_attr))
        self.assertTrue(hasattr(mod, existing_attr))

        if cache_filename:
            # A valid .pyc should not be written again. (We can't use the set_mode technique
            # here because failure to write a .pyc is silently ignored.)
            with self.assertNotModifies(cache_filename):
                mod = self.clean_reload(mod)
            self.assertFalse(hasattr(mod, new_attr))

            # And if the header matches, the code in the .pyc should be used, whatever it is.
            header = self.read_pyc_header(cache_filename)
            with open(cache_filename, "wb") as pyc_file:
                pyc_file.write(header)
                code = compile(f"{new_attr} = 2", "<test>", "exec")
                marshal.dump(code, pyc_file)
            mod = self.clean_reload(mod)
            self.assertEqual(2, getattr(mod, new_attr))
            self.assertFalse(hasattr(mod, existing_attr))

            # A .pyc with mismatching header timestamp should be written again.
            new_header = header[0:4] + b"\x00\x01\x02\x03" + header[8:]
            self.assertNotEqual(new_header, header)
            self.write_pyc_header(cache_filename, new_header)
            with self.assertModifies(cache_filename):
                self.clean_reload(mod)
            self.assertEqual(header, self.read_pyc_header(cache_filename))

    def read_pyc_header(self, filename):
        with open(filename, "rb") as pyc_file:
            return pyc_file.read(12)

    def write_pyc_header(self, filename, header):
        with open(filename, "r+b") as pyc_file:
            pyc_file.seek(0)
            pyc_file.write(header)

    def test_so(self):
        reqs_zip = REQS_ABI_ZIP if multi_abi else REQS_COMMON_ZIP
        filename = asset_path(reqs_zip, "markupsafe/_speedups.so")
        mod = self.check_module("markupsafe._speedups", filename, filename)
        self.check_extract_if_changed(mod, filename)

    def test_data(self):
        # App ZIP
        # .py files should never be extracted.
        self.check_data(APP_ZIP, "chaquopy", "test/test_android.py",
                        '"""This file tests internal details of AndroidPlatform.',
                        extract=False)
        # .so files should only be extracted when imported (see test_so).
        self.check_data(APP_ZIP, "chaquopy", "test/resources/b.so", "bravo", extract=False)
        # Other files should always be extracted.
        self.check_data(APP_ZIP, "chaquopy", "test/resources/a.txt", "alpha", extract=True)

        # Requirements ZIP
        self.check_data(REQS_COMMON_ZIP, "markupsafe", "_constants.pyc", MAGIC_NUMBER,
                        extract=False)
        self.check_data(REQS_ABI_ZIP, "markupsafe", "_speedups.so", b"\x7fELF", extract=False)
        self.check_data(REQS_COMMON_ZIP, "certifi", "cacert.pem",
                        "\n# Issuer: CN=GlobalSign Root CA O=GlobalSign nv-sa OU=Root CA",
                        extract=True)

        import murmurhash.about
        loader = murmurhash.about.__loader__
        zip_name = REQS_COMMON_ZIP
        with self.assertRaisesRegexp(ValueError,
                                     r"AssetFinder\('{}'\) can't access '/invalid.py'"
                                     .format(asset_path(zip_name, "murmurhash"))):
            loader.get_data("/invalid.py")
        with self.assertRaisesRegexp(FileNotFoundError, "invalid.py"):
            loader.get_data(asset_path(zip_name, "invalid.py"))

    def check_data(self, zip_name, package, filename, start, *, extract):
        # Extraction is triggered only when a top-level package is imported.
        self.assertNotIn(".", package)

        cache_filename = asset_path(zip_name, package, filename)
        if exists(cache_filename):
            os.remove(cache_filename)

        mod = import_module(package)
        data = pkgutil.get_data(package, filename)
        if isinstance(start, str):
            start = start.encode("UTF-8")
        self.assertTrue(data.startswith(start))

        if extract:
            self.check_extract_if_changed(mod, cache_filename)
            with open(cache_filename, "rb") as cache_file:
                self.assertEqual(data, cache_file.read())
        else:
            self.assertNotPredicate(exists, cache_filename)

    def check_extract_if_changed(self, mod, cache_filename):
        # A missing file should be extracted.
        if exists(cache_filename):
            os.remove(cache_filename)
        mod = self.clean_reload(mod)
        self.assertPredicate(exists, cache_filename)

        # An unchanged file should not be extracted again.
        with self.set_mode(cache_filename, "444"):
            mod = self.clean_reload(mod)

        # A file with mismatching mtime should be extracted again.
        original_mtime = os.stat(cache_filename).st_mtime
        os.utime(cache_filename, None)
        with self.set_mode(cache_filename, "444"):
            with self.assertRaisesRegexp(OSError, "Permission denied"):
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

    def check_module(self, mod_name, filename, cache_filename, *, is_package=False,
                     source_head=None):
        mod = import_module(mod_name)
        if cache_filename:
            # A missing cache file should be created.
            if exists(cache_filename):
                os.remove(cache_filename)
            mod = self.clean_reload(mod)
            self.assertPredicate(exists, cache_filename)

        # Module attributes
        self.assertEqual(mod_name, mod.__name__)
        self.assertEqual(filename, mod.__file__)
        self.assertEqual(filename.endswith(".so"), exists(mod.__file__))
        if is_package:
            self.assertEqual([dirname(filename)], mod.__path__)
            self.assertEqual(mod_name, mod.__package__)
        else:
            self.assertFalse(hasattr(mod, "__path__"))
            self.assertEqual(mod_name.rpartition(".")[0], mod.__package__)
        loader = mod.__loader__
        self.assertIsInstance(loader, importer.AssetLoader)

        # Loader methods (get_data is tested elsewhere)
        self.assertEqual(is_package, loader.is_package(mod_name))
        self.assertIsInstance(loader.get_code(mod_name),
                              types.CodeType if filename.endswith(".py") else type(None))

        source = loader.get_source(mod_name)
        if source_head:
            self.assertTrue(source.startswith(source_head), repr(source))
        else:
            self.assertIsNone(source)

        expected_file = loader.get_filename(mod_name)
        if expected_file.endswith(".pyc"):
            expected_file = expected_file[:-1]
        self.assertEqual(expected_file, mod.__file__)

        return mod

    # Verify that the traceback builder can get source code from the loader in all contexts.
    # (The "package1" test files are also used in test_import.py.)
    def test_exception(self):
        test_frame = (fr'  File "{asset_path(APP_ZIP)}/chaquopy/test/test_android.py", '
                      fr'line \d+, in test_exception\n'
                      fr'    .+?\n')  # Source code line from this file.
        import_frame = r'  File "import.pxi", line \d+, in java.chaquopy.import_override\n'

        # Compilation
        try:
            from package1 import syntax_error  # noqa
        except SyntaxError:
            self.assertRegexpMatches(
                format_exc(),
                test_frame + import_frame +
                fr'  File "{asset_path(APP_ZIP)}/package1/syntax_error.py", line 1\n'
                fr'    one two\n'
                fr'          \^\n'
                fr'SyntaxError: invalid syntax\n$')
        else:
            self.fail()

        # Module execution
        try:
            from package1 import recursive_import_error  # noqa
        except ImportError:
            self.assertRegexpMatches(
                format_exc(),
                test_frame + import_frame +
                fr'  File "{asset_path(APP_ZIP)}/package1/recursive_import_error.py", '
                fr'line 1, in <module>\n'
                fr'    from os import nonexistent\n'
                fr"ImportError: cannot import name 'nonexistent'\n$")
        else:
            self.fail()

        # Module execution (recursive import)
        try:
            from package1 import recursive_other_error  # noqa
        except ValueError:
            self.assertRegexpMatches(
                format_exc(),
                test_frame + import_frame +
                fr'  File "{asset_path(APP_ZIP)}/package1/recursive_other_error.py", '
                fr'line 1, in <module>\n'
                fr'    from . import other_error  # noqa: F401\n' +
                import_frame +
                fr'  File "{asset_path(APP_ZIP)}/package1/other_error.py", '
                fr'line 1, in <module>\n'
                fr'    int\("hello"\)\n'
                fr"ValueError: invalid literal for int\(\) with base 10: 'hello'\n$")
        else:
            self.fail()

        # After import complete.
        # Frames from pre-compiled requirements should have no source code.
        class C(object):
            __html__ = None
        try:
            from markupsafe import _native
            _native.escape(C)
        except TypeError:
            self.assertRegexpMatches(
                format_exc(),
                test_frame +
                fr'  File "{asset_path(REQS_COMMON_ZIP)}/markupsafe/_native.py", '
                fr'line 21, in escape\n'
                fr"TypeError: 'NoneType' object is not callable\n$")
        else:
            self.fail()

        # Frames from pre-compiled stdlib should have no source code.
        try:
            import json
            json.loads("hello")
        except json.JSONDecodeError:
            self.assertRegexpMatches(
                format_exc(),
                test_frame +
                r'  File "stdlib/json/__init__.py", line 354, in loads\n'
                r'  File "stdlib/json/decoder.py", line 339, in decode\n'
                r'  File "stdlib/json/decoder.py", line 357, in raw_decode\n'
                r'json.decoder.JSONDecodeError: Expecting value: line 1 column 1 \(char 0\)\n$')
        else:
            self.fail()

    def test_imp(self):
        self.longMessage = True
        with self.assertRaisesRegexp(ImportError, "No module named 'nonexistent'"):
            imp.find_module("nonexistent")

        # If any of the below modules already exist, they will be reloaded. This may have
        # side-effects, e.g. if we'd included sys, then sys.executable would be reset and
        # test_sys below would fail.
        for mod_name, expected_type in [
                ("email", imp.PKG_DIRECTORY),                   # stdlib
                ("argparse", imp.PY_COMPILED),                  #
                ("select", imp.C_EXTENSION),                    #
                ("errno", imp.C_BUILTIN),                       #
                ("markupsafe", imp.PKG_DIRECTORY),              # requirements
                ("markupsafe._native", imp.PY_COMPILED),        #
                ("markupsafe._speedups", imp.C_EXTENSION),      #
                ("chaquopy.utils", imp.PKG_DIRECTORY),          # app (already loaded)
                ("imp_test", imp.PY_SOURCE)]:                   #     (not already loaded)
            with self.subTest(mod_name=mod_name):
                path = None
                prefix = ""
                words = mod_name.split(".")
                for i, word in enumerate(words):
                    prefix += word
                    with self.subTest(prefix=prefix):
                        file, pathname, description = imp.find_module(word, path)
                        suffix, mode, actual_type = description
                        mod = imp.load_module(prefix, file, pathname, description)
                        self.assertEqual(prefix, mod.__name__)
                        self.assertEqual(actual_type == imp.PKG_DIRECTORY,
                                         hasattr(mod, "__path__"))

                        self.assertTrue(hasattr(mod, "__spec__"))
                        self.assertIsNotNone(mod.__spec__)
                        self.assertEqual(mod.__name__, mod.__spec__.name)

                        if actual_type == imp.C_BUILTIN:
                            self.assertIsNone(file)
                            self.assertIsNone(pathname)
                        else:
                            if actual_type == imp.PKG_DIRECTORY:
                                self.assertIsNone(file)
                            else:
                                # Our implementation of load_module doesn't use `file`, but
                                # user code might, so check it adequately simulates a file.
                                self.assertTrue(hasattr(file, "read"))
                                self.assertTrue(hasattr(file, "close"))
                            self.assertIsNotNone(pathname)
                            self.assertTrue(hasattr(mod, "__file__"))

                        if i < len(words) - 1:
                            self.assertEqual(imp.PKG_DIRECTORY, actual_type)
                            prefix += "."
                            path = mod.__path__
                        else:
                            self.assertEqual(expected_type, actual_type)

    # This trick was used by Electron Cash to load modules under a different name. The Electron
    # Cash Android app no longer needs it, but there may be other software which does.
    def test_imp_rename(self):
        # Renames in stdlib are not currently supported.
        with self.assertRaisesRegexp(ImportError, "zipimporter does not support loading module "
                                     "'json' under a different name 'jason'"):
            imp.load_module("jason", *imp.find_module("json"))

        def check_top_level(real_name, load_name, id):
            mod_renamed = imp.load_module(load_name, *imp.find_module(real_name))
            self.assertEqual(load_name, mod_renamed.__name__)
            self.assertEqual(id, mod_renamed.ID)
            self.assertIs(mod_renamed, import_module(load_name))

            mod_original = import_module(real_name)
            self.assertEqual(real_name, mod_original.__name__)
            self.assertIsNot(mod_renamed, mod_original)
            self.assertEqual(mod_renamed.ID, mod_original.ID)
            self.assertEqual(mod_renamed.__file__, mod_original.__file__)

        check_top_level("imp_rename_one", "imp_rename_1", "1")  # Module
        check_top_level("imp_rename_two", "imp_rename_2", "2")  # Package

        import imp_rename_two  # Original
        import imp_rename_2    # Renamed
        path = [asset_path(APP_ZIP, "imp_rename_two")]
        self.assertEqual(path, imp_rename_two.__path__)
        self.assertEqual(path, imp_rename_2.__path__)

        # Non-renamed sub-modules
        from imp_rename_2 import mod_one, pkg_two
        for mod, name, id in [(mod_one, "mod_one", "21"), (pkg_two, "pkg_two", "22")]:
            self.assertFalse(hasattr(imp_rename_two, name), name)
            mod_attr = getattr(imp_rename_2, name)
            self.assertIs(mod_attr, mod)
            self.assertEqual("imp_rename_2." + name, mod.__name__)
            self.assertEqual(id, mod.ID)
        self.assertEqual([asset_path(APP_ZIP, "imp_rename_two/pkg_two")], pkg_two.__path__)

        # Renamed sub-modules
        mod_3 = imp.load_module("imp_rename_2.mod_3",
                                *imp.find_module("mod_three", imp_rename_two.__path__))
        self.assertEqual("imp_rename_2.mod_3", mod_3.__name__)
        self.assertEqual("23", mod_3.ID)
        self.assertIs(sys.modules["imp_rename_2.mod_3"], mod_3)

        # The standard load_module implementation doesn't add a sub-module as an attribute of
        # its package. (Despite this, in Python 3 only, it can still be imported under its new
        # name using `from ... import`. This seems to contradict the documentation of
        # __import__, but it's not important enough to investigate just now.)
        self.assertFalse(hasattr(imp_rename_2, "mod_3"))

    # See src/test/python/test.pth.
    def test_pth(self):
        import pth_generated
        self.assertFalse(hasattr(pth_generated, "__file__"))
        self.assertEqual([asset_path(APP_ZIP, "pth_generated")], pth_generated.__path__)
        for entry in sys.path:
            self.assertNotIn("nonexistent", entry)

    def test_iter_modules(self):
        def check_iter_modules(mod, expected):
            mod_infos = list(pkgutil.iter_modules(mod.__path__))
            self.assertCountEqual(expected, [(mi.name, mi.ispkg) for mi in mod_infos])
            finders = [pkgutil.get_importer(p) for p in mod.__path__]
            for mi in mod_infos:
                self.assertIn(mi.module_finder, finders, mi)

        import murmurhash.tests
        check_iter_modules(murmurhash, [("about", False),   # Pure-Python module
                                        ("mrmr", False),    # Native module
                                        ("tests", True)])   # Package
        check_iter_modules(murmurhash.tests, [("test_import", False)])

        self.assertCountEqual([("murmurhash.about", False), ("murmurhash.mrmr", False),
                               ("murmurhash.tests", True),
                               ("murmurhash.tests.test_import", False)],
                              [(mi.name, mi.ispkg) for mi in
                               pkgutil.walk_packages(murmurhash.__path__, "murmurhash.")])

    def test_pkg_resources_working_set(self):
        import pkg_resources as pr
        self.assertCountEqual(["MarkupSafe", "Pygments", "certifi", "chaquopy-gnustl",
                               "murmurhash", "setuptools"],
                              [dist.project_name for dist in pr.working_set])
        self.assertEqual("40.4.3", pr.get_distribution("setuptools").version)

    def test_pkg_resources_resources(self):
        import pkg_resources as pr
        self.assertTrue(pr.resource_exists(__package__, "test_android.py"))
        self.assertTrue(pr.resource_exists(__package__, "resources"))
        self.assertFalse(pr.resource_exists(__package__, "nonexistent"))
        self.assertTrue(pr.resource_exists(__package__, "resources/a.txt"))
        self.assertFalse(pr.resource_exists(__package__, "resources/nonexistent.txt"))

        self.assertFalse(pr.resource_isdir(__package__, "test_android.py"))
        self.assertTrue(pr.resource_isdir(__package__, "resources"))
        self.assertFalse(pr.resource_isdir(__package__, "nonexistent"))

        self.assertCountEqual(["a.txt", "b.so", "subdir"],
                              pr.resource_listdir(__package__, "resources"))
        self.assertEqual(b"alpha\n", pr.resource_string(__package__, "resources/a.txt"))
        self.assertEqual(b"bravo\n", pr.resource_string(__package__, "resources/b.so"))
        self.assertCountEqual(["c.txt"], pr.resource_listdir(__package__, "resources/subdir"))
        self.assertEqual(b"charlie\n", pr.resource_string(__package__, "resources/subdir/c.txt"))

        # App ZIP
        a_filename = pr.resource_filename(__package__, "resources/a.txt")
        self.assertEqual(asset_path(APP_ZIP, "chaquopy/test/resources/a.txt"), a_filename)
        with open(a_filename) as a_file:
            self.assertEqual("alpha\n", a_file.read())

        # Requirements ZIP
        cacert_filename = pr.resource_filename("certifi", "cacert.pem")
        self.assertEqual(asset_path(REQS_COMMON_ZIP, "certifi/cacert.pem"), cacert_filename)
        with open(cacert_filename) as cacert_file:
            self.assertTrue(cacert_file.read().startswith(
                "\n# Issuer: CN=GlobalSign Root CA O=GlobalSign nv-sa OU=Root CA"))

    def assertModifies(self, filename):
        return self.check_modifies(self.assertNotEqual, filename)

    def assertNotModifies(self, filename):
        return self.check_modifies(self.assertEqual, filename)

    @contextmanager
    def check_modifies(self, assertion, filename):
        # The Android filesystem may only have 1-second resolution, and Device File Explorer
        # only has 1-minute resolution, so we need to set the mtime to something at least that
        # far away from the current time.
        original_mtime = os.stat(filename).st_mtime
        test_mtime = original_mtime - 60
        os.utime(filename, (test_mtime, test_mtime))
        try:
            yield
            assertion(test_mtime, os.stat(filename).st_mtime)
        finally:
            os.utime(filename, (original_mtime, original_mtime))

    def assertPredicate(self, f, *args):
        self.check_predicate(self.assertTrue, f, *args)

    def assertNotPredicate(self, f, *args):
        self.check_predicate(self.assertFalse, f, *args)

    def check_predicate(self, assertion, f, *args):
        assertion(f(*args), f"{f.__name__}{args!r}")


def asset_path(zip_name, *paths):
    return join(context.getFilesDir().toString(),
                "chaquopy/AssetFinder",
                os.path.splitext(zip_name)[0].partition("-")[0],
                *paths)


class TestAndroidStdlib(unittest.TestCase):

    def test_ctypes(self):
        import ctypes
        from ctypes.util import find_library

        self.assertEqual("libc.so", find_library("c"))
        self.assertEqual("liblog.so", find_library("log"))
        self.assertIsNone(find_library("nonexistent"))

        self.assertTrue(ctypes.pythonapi.PyLong_FromString)

    def test_lib2to3(self):
        # Requires grammar files to be available in stdlib zip.
        from lib2to3 import pygram  # noqa: F401

    def test_hashlib(self):
        import hashlib
        INPUT = b"The quick brown fox jumps over the lazy dog"
        TESTS = [
            ("sha1", "2fd4e1c67a2d28fced849ee1bb76e7391b93eb12"),
            ("sha3_512", ("01dedd5de4ef14642445ba5f5b97c15e47b9ad931326e4b0727cd94cefc44fff23f"
                          "07bf543139939b49128caf436dc1bdee54fcb24023a08d9403f9b4bf0d450")),
            ("blake2b", ("a8add4bdddfd93e4877d2746e62817b116364a1fa7bc148d95090bc7333b3673f8240"
                         "1cf7aa2e4cb1ecd90296e3f14cb5413f8ed77be73045b13914cdcd6a918")),
            ("ripemd160", "37f332f68db77bd9d7edd4969571ad671cf9dd3b"),  # OpenSSL-only
        ]
        for name, expected in TESTS:
            with self.subTest(algorithm=name):
                # With initial data
                self.assertEqual(expected, hashlib.new(name, INPUT).hexdigest())
                # Without initial data
                h = hashlib.new(name)
                h.update(INPUT)
                self.assertEqual(expected, h.hexdigest())

                if name in hashlib.algorithms_guaranteed:
                    # With initial data
                    self.assertEqual(expected, getattr(hashlib, name)(INPUT).hexdigest())
                    # Without initial data
                    h = getattr(hashlib, name)()
                    h.update(INPUT)
                    self.assertEqual(expected, h.hexdigest())
                else:
                    self.assertFalse(hasattr(hashlib, name))

    def test_locale(self):
        import locale
        self.assertEqual("UTF-8", locale.getlocale()[1])
        self.assertEqual("UTF-8", locale.getdefaultlocale()[1])
        self.assertEqual("UTF-8", locale.getpreferredencoding())
        self.assertEqual("utf-8", sys.getdefaultencoding())
        self.assertEqual("utf-8", sys.getfilesystemencoding())

    def test_os(self):
        self.assertEqual("posix", os.name)
        self.assertEqual(str(context.getFilesDir()), os.path.expanduser("~"))

    def test_platform(self):
        # Requires sys.executable to exist.
        import platform
        p = platform.platform()
        self.assertRegexpMatches(p, r"^Linux")

    def test_select(self):
        import select
        self.assertFalse(hasattr(select, "kevent"))
        self.assertFalse(hasattr(select, "kqueue"))

        import selectors
        self.assertIs(selectors.DefaultSelector, selectors.EpollSelector)

    def test_sqlite(self):
        import sqlite3
        conn = sqlite3.connect(":memory:")
        conn.execute("create table test (a text, b text)")
        conn.execute("insert into test values ('alpha', 'one'), ('bravo', 'two')")
        cur = conn.execute("select b from test where a = 'bravo'")
        self.assertEqual([("two",)], cur.fetchall())

    def test_ssl(self):
        from urllib.request import urlopen
        resp = urlopen("https://chaquo.com/chaquopy/")
        self.assertEqual(200, resp.getcode())
        self.assertRegexpMatches(resp.info()["Content-type"], r"^text/html")

    def test_sys(self):
        self.assertEqual("m", sys.abiflags)
        self.assertEqual([""], sys.argv)
        self.assertTrue(exists(sys.executable), sys.executable)
        for p in sys.path:
            self.assertIsInstance(p, str)
            self.assertTrue(exists(p), p)
        self.assertRegexpMatches(sys.platform, r"^linux")

    def test_sysconfig(self):
        import distutils.sysconfig
        import sysconfig
        ldlibrary = "libpython{}.{}m.so".format(*sys.version_info[:2])
        self.assertEqual(ldlibrary, sysconfig.get_config_vars()["LDLIBRARY"])
        self.assertEqual(ldlibrary, distutils.sysconfig.get_config_vars()["LDLIBRARY"])

    def test_tempfile(self):
        import tempfile
        expected_dir = join(str(context.getCacheDir()), "chaquopy/tmp")
        self.assertEqual(expected_dir, tempfile.gettempdir())
        with tempfile.NamedTemporaryFile() as f:
            self.assertEqual(expected_dir, dirname(f.name))


class TestAndroidStreams(unittest.TestCase):

    maxDiff = None

    def setUp(self):
        from android.util import Log
        Log.i(*self.get_marker())
        self.expected_log = []

    def write(self, stream, s, expected_log):
        self.assertEqual(len(s), stream.write(s))
        self.expected_log += expected_log

    def tearDown(self):
        actual_log = None
        marker = "I/{}: {}".format(*self.get_marker())
        for line in check_output(shlex.split("logcat -d -v tag")).decode("UTF-8").splitlines():
            if line == marker:
                actual_log = []
            elif actual_log is not None and "/python.std" in line:
                actual_log.append(line)
        self.assertEqual(self.expected_log, actual_log)

    def get_marker(self):
        cls_name, test_name = self.id().split(".")[-2:]
        return cls_name, test_name

    def test_output(self):
        out = sys.stdout
        err = sys.stderr
        for stream in [out, err]:
            self.assertTrue(stream.writable())
            self.assertFalse(stream.readable())

        self.write(out, "a",             ["I/python.stdout: a"])
        self.write(out, "Hello world",   ["I/python.stdout: Hello world"])
        self.write(err, "Hello stderr",  ["W/python.stderr: Hello stderr"])
        self.write(out, " ",             ["I/python.stdout:  "])
        self.write(out, "  ",            ["I/python.stdout:   "])

        # Non-ASCII text
        for s in ["ol\u00e9",        # Spanish
                  "\u4e2d\u6587"]:   # Chinese
            self.write(out, s, ["I/python.stdout: " + s])

        # Empty lines can't be logged, so we change them to a space. Empty strings, on the
        # other hand, should be ignored.
        #
        # Avoid repeating log messages as it may activate "chatty" filtering and break the
        # tests. Also, it makes debugging easier.
        self.write(out, "",              [])
        self.write(out, "\n",            ["I/python.stdout:  "])
        self.write(out, "\na",           ["I/python.stdout:  ",
                                          "I/python.stdout: a"])
        self.write(out, "b\n",           ["I/python.stdout: b"])
        self.write(out, "c\n\n",         ["I/python.stdout: c",
                                          "I/python.stdout:  "])
        self.write(out, "d\ne",          ["I/python.stdout: d",
                                          "I/python.stdout: e"])
        self.write(out, "f\n\ng",        ["I/python.stdout: f",
                                          "I/python.stdout:  ",
                                          "I/python.stdout: g"])

    # The maximum line length is 4000.
    def test_output_long(self):
        self.write(sys.stdout, "foobar" * 700,
                   ["I/python.stdout: " + ("foobar" * 666) + "foob",
                    "I/python.stdout: ar" + ("foobar" * 33)])

    def test_input(self):
        self.assertTrue(sys.stdin.readable())
        self.assertFalse(sys.stdin.writable())
        self.assertEqual("", sys.stdin.read())
        self.assertEqual("", sys.stdin.read(42))
        self.assertEqual("", sys.stdin.readline())
        self.assertEqual("", sys.stdin.readline(42))
