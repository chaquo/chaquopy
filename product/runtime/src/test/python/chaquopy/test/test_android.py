"""This file tests internal details of AndroidPlatform. These are not part of the public API,
and should not be accessed or relied upon by user code.
"""

import calendar
from contextlib import contextmanager
import imp
from importlib import import_module, metadata, reload, resources
import importlib.util
from importlib.util import cache_from_source, MAGIC_NUMBER
import marshal
import os
from os.path import dirname, exists, join, realpath, splitext
import pkgutil
import platform
import re
from shutil import rmtree
import subprocess
import sys
from traceback import format_exc
import types
import unittest

from .test_utils import API_LEVEL, FilterWarningsCase


# Flags from PEP 3149.
ABI_FLAGS = ""

REQUIREMENTS = ["chaquopy-libcxx", "murmurhash", "Pygments"]

if API_LEVEL:
    from android.os import Build
    from com.chaquo.python.android import AndroidPlatform
    from java.android import importer

    context = __loader__.finder.context  # noqa: F821
    APP_ZIP = "app"
    REQS_COMMON_ZIP = "requirements-common"
    multi_abi = len([name for name in context.getAssets().list("chaquopy")
                     if name.startswith("requirements")]) > 2
    ABI = AndroidPlatform.ABI
    REQS_ABI_ZIP = f"requirements-{ABI}" if multi_abi else REQS_COMMON_ZIP

    # REQS_COMMON_ZIP and REQS_ABI_ZIP are now both extracted into the same directory, but we
    # maintain the distinction in the tests in case that changes again in the future.
    def asset_path(zip_name, *paths):
        return join(realpath(context.getFilesDir().toString()), "chaquopy/AssetFinder",
                    zip_name.partition("-")[0], *paths)

    LIBCXX_FILENAME = asset_path(REQS_ABI_ZIP, "chaquopy/lib/libc++_shared.so")


def setUpModule():
    if API_LEVEL is None:
        raise unittest.SkipTest("Not running on Android")

class AndroidTestCase(FilterWarningsCase):
    def assertPredicate(self, f, *args):
        self.check_predicate(self.assertTrue, f, *args)

    def assertNotPredicate(self, f, *args):
        self.check_predicate(self.assertFalse, f, *args)

    def check_predicate(self, assertion, f, *args):
        assertion(f(*args), f"{f.__name__}{args!r}")


class TestAndroidPlatform(AndroidTestCase):

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

    def test_files(self):
        chaquopy_dir = join(str(context.getFilesDir()), "chaquopy")
        self.assertCountEqual(["AssetFinder", "bootstrap-native", "bootstrap.imy",
                               "cacert.pem", "stdlib-common.imy", "ticket.txt"],
                              os.listdir(chaquopy_dir))
        bn_dir = f"{chaquopy_dir}/bootstrap-native"
        self.assertCountEqual([ABI], os.listdir(bn_dir))

        for subdir, entries in [
            (ABI, ["java", "_csv.so", "_ctypes.so", "_datetime.so", "_hashlib.so", "_json.so",
                   "_random.so", "_struct.so", "binascii.so",  "math.so", "mmap.so", "zlib.so"]),
            (f"{ABI}/java", ["chaquopy.so", "chaquopy_android.so"]),
        ]:
            with self.subTest(subdir=subdir):
                # Create a stray file which should be removed on the next startup.
                pid_txt = f"{os.getpid()}.txt"
                with open(f"{bn_dir}/{subdir}/{pid_txt}", "w"):
                    pass
                self.assertCountEqual(entries + [pid_txt], os.listdir(f"{bn_dir}/{subdir}"))


class TestAndroidImport(AndroidTestCase):

    def test_init(self):
        self.check_py("murmurhash", REQS_COMMON_ZIP, "murmurhash/__init__.py", "get_include",
                      is_package=True)
        self.check_py("android1", APP_ZIP, "android1/__init__.py", "x",
                      source_head="# This package is used by test_android.", is_package=True)

    def test_py(self):
        self.check_py("murmurhash.about", REQS_COMMON_ZIP, "murmurhash/about.py", "__summary__")
        self.check_py("android1.mod1", APP_ZIP, "android1/mod1.py",
                      "x", source_head='x = "android1.mod1"')

    def check_py(self, mod_name, zip_name, zip_path, existing_attr, **kwargs):
        filename = asset_path(zip_name, zip_path)
        # build.gradle has pyc { src false }, so APP_ZIP will generate __pycache__ directories.
        cache_filename = cache_from_source(filename) if zip_name == APP_ZIP else None
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
            # A valid .pyc should not be written again.
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
            new_header = header[0:8] + b"\x00\x01\x02\x03" + header[12:]
            self.assertNotEqual(new_header, header)
            self.write_pyc_header(cache_filename, new_header)
            with self.assertModifies(cache_filename):
                self.clean_reload(mod)
            self.assertEqual(header, self.read_pyc_header(cache_filename))

    def read_pyc_header(self, filename):
        with open(filename, "rb") as pyc_file:
            return pyc_file.read(16)

    def write_pyc_header(self, filename, header):
        with open(filename, "r+b") as pyc_file:
            pyc_file.seek(0)
            pyc_file.write(header)

    def test_so(self):
        filename = asset_path(REQS_ABI_ZIP, "murmurhash/mrmr.so")
        mod = self.check_module("murmurhash.mrmr", filename, filename)
        self.check_extract_if_changed(mod, filename)

    def test_non_package_data(self):
        for dir_name, dir_description in [("", "root"), ("non_package_data", "directory"),
                                          ("non_package_data/subdir", "subdirectory")]:
            with self.subTest(dir_name=dir_name):
                extracted_dir = asset_path(APP_ZIP, dir_name)
                self.assertCountEqual(
                    ["non_package_data.txt"] + (["test.pth"] if not dir_name else []),
                    [entry.name for entry in os.scandir(extracted_dir) if entry.is_file()])
                with open(join(extracted_dir, "non_package_data.txt")) as f:
                    self.assertPredicate(str.startswith, f.read(),
                                         f"# Text file in {dir_description}")

        # Package directories shouldn't be extracted on startup, but on first import. This
        # package is never imported, so it should never be extracted at all.
        self.assertNotPredicate(exists, asset_path(APP_ZIP, "never_imported"))

    def test_package_data(self):
        # App ZIP
        pkg = "android1"
        self.check_data(APP_ZIP, pkg, "__init__.py", b"# This package is")
        self.check_data(APP_ZIP, pkg, "b.so", b"bravo")
        self.check_data(APP_ZIP, pkg, "a.txt", b"alpha")
        self.check_data(APP_ZIP, pkg, "subdir/c.txt", b"charlie")

        # Requirements ZIP
        self.check_data(REQS_COMMON_ZIP, "murmurhash", "about.pyc", MAGIC_NUMBER)
        self.check_data(REQS_ABI_ZIP, "murmurhash", "mrmr.so", b"\x7fELF")
        self.check_data(REQS_COMMON_ZIP, "murmurhash", "mrmr.pxd", b"from libc.stdint")

        import murmurhash.about
        loader = murmurhash.about.__loader__
        zip_name = REQS_COMMON_ZIP
        with self.assertRaisesRegex(ValueError,
                                    r"AssetFinder\('{}'\) can't access '/invalid.py'"
                                    .format(asset_path(zip_name, "murmurhash"))):
            loader.get_data("/invalid.py")
        with self.assertRaisesRegex(FileNotFoundError, "invalid.py"):
            loader.get_data(asset_path(zip_name, "invalid.py"))

    def check_data(self, zip_name, package, filename, start):
        # Extraction is triggered only when a top-level package is imported.
        self.assertNotIn(".", package)

        cache_filename = asset_path(zip_name, package, filename)
        if exists(cache_filename):
            os.remove(cache_filename)

        mod = import_module(package)
        data = pkgutil.get_data(package, filename)
        self.assertTrue(data.startswith(start))

        if splitext(filename)[1] in [".py", ".pyc", ".so"]:
            # Importable files are not extracted.
            self.assertNotPredicate(exists, cache_filename)
        else:
            self.check_extract_if_changed(mod, cache_filename)
            with open(cache_filename, "rb") as cache_file:
                self.assertEqual(data, cache_file.read())

    def check_extract_if_changed(self, mod, cache_filename):
        # A missing file should be extracted.
        if exists(cache_filename):
            os.remove(cache_filename)
        mod = self.clean_reload(mod)
        self.assertPredicate(exists, cache_filename)

        # An unchanged file should not be extracted again.
        with self.assertNotModifies(cache_filename):
            mod = self.clean_reload(mod)

        # A file with mismatching mtime should be extracted again.
        original_mtime = os.stat(cache_filename).st_mtime
        os.utime(cache_filename, None)
        with self.assertModifies(cache_filename):
            self.clean_reload(mod)
        self.assertEqual(original_mtime, os.stat(cache_filename).st_mtime)

    def clean_reload(self, mod):
        sys.modules.pop(mod.__name__, None)
        submod_names = [name for name in sys.modules if name.startswith(mod.__name__ + ".")]
        for name in submod_names:
            sys.modules.pop(name)

        new_mod = import_module(mod.__name__)
        self.assertIsNot(new_mod, mod)
        return new_mod

    def check_module(self, mod_name, filename, cache_filename, *, is_package=False,
                     source_head=None):
        if cache_filename and exists(cache_filename):
            os.remove(cache_filename)
        mod = import_module(mod_name)
        mod = self.clean_reload(mod)
        if cache_filename:
            self.assertPredicate(exists, cache_filename)

        # Module attributes
        self.assertEqual(mod_name, mod.__name__)
        self.assertEqual(filename, mod.__file__)
        self.assertEqual(realpath(mod.__file__), mod.__file__)
        self.assertEqual(filename.endswith(".so"), exists(mod.__file__))
        if is_package:
            self.assertEqual([dirname(filename)], mod.__path__)
            self.assertEqual(realpath(mod.__path__[0]), mod.__path__[0])
            self.assertEqual(mod_name, mod.__package__)
        else:
            self.assertFalse(hasattr(mod, "__path__"))
            self.assertEqual(mod_name.rpartition(".")[0], mod.__package__)
        loader = mod.__loader__
        self.assertIsInstance(loader, importer.AssetLoader)
        spec = mod.__spec__
        self.assertEqual(mod_name, spec.name)
        self.assertIs(loader, spec.loader)
        # spec.origin and the extract_so symlink workaround are covered by pyzmq/test.py.

        # Loader methods (get_data is tested elsewhere)
        self.assertEqual(is_package, loader.is_package(mod_name))
        self.assertIsInstance(loader.get_code(mod_name),
                              types.CodeType if filename.endswith(".py") else type(None))

        source = loader.get_source(mod_name)
        if source_head:
            self.assertTrue(source.startswith(source_head), repr(source))
        else:
            self.assertIsNone(source)

        self.assertEqual(re.sub(r"\.pyc$", ".py", loader.get_filename(mod_name)),
                         mod.__file__)

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
            self.assertRegex(
                format_exc(),
                test_frame + import_frame +
                fr'  File "{asset_path(APP_ZIP)}/package1/syntax_error.py", line 1\n'
                fr'    one two\n'
                fr'        \^\n'
                fr'SyntaxError: invalid syntax\n$')
        else:
            self.fail()

        # Module execution
        try:
            from package1 import recursive_import_error  # noqa
        except ImportError:
            self.assertRegex(
                format_exc(),
                test_frame + import_frame +
                fr'  File "{asset_path(APP_ZIP)}/package1/recursive_import_error.py", '
                fr'line 1, in <module>\n'
                fr'    from os import nonexistent\n'
                fr"ImportError: cannot import name 'nonexistent' from 'os'")
        else:
            self.fail()

        # Module execution (recursive import)
        try:
            from package1 import recursive_other_error  # noqa
        except ValueError:
            self.assertRegex(
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
        try:
            import murmurhash
            murmurhash_file = murmurhash.__file__
            del murmurhash.__file__
            murmurhash.get_include()
        except NameError:
            self.assertRegex(
                format_exc(),
                test_frame +
                fr'  File "{asset_path(REQS_COMMON_ZIP)}/murmurhash/__init__.py", '
                fr'line 5, in get_include\n'
                fr"NameError: name '__file__' is not defined\n$")
        else:
            self.fail()
        finally:
            murmurhash.__file__ = murmurhash_file

        # Frames from pre-compiled stdlib should have filenames starting with "stdlib/", and no
        # source code.
        try:
            import json
            json.loads("hello")
        except json.JSONDecodeError:
            self.assertRegex(
                format_exc(),
                test_frame +
                r'  File "stdlib/json/__init__.py", line \d+, in loads\n'
                r'  File "stdlib/json/decoder.py", line \d+, in decode\n'
                r'  File "stdlib/json/decoder.py", line \d+, in raw_decode\n'
                r'json.decoder.JSONDecodeError: Expecting value: line 1 column 1 \(char 0\)\n$')
        else:
            self.fail()

    def test_imp(self):
        with self.assertRaisesRegex(ImportError, "No module named 'nonexistent'"):
            imp.find_module("nonexistent")

        # See comment about torchvision below.
        from murmurhash import mrmr
        os.remove(mrmr.__file__)

        # If any of the below modules already exist, they will be reloaded. This may have
        # side-effects, e.g. if we'd included sys, then sys.executable would be reset and
        # test_sys below would fail.
        for mod_name, expected_type in [
                ("email", imp.PKG_DIRECTORY),                   # stdlib
                ("argparse", imp.PY_COMPILED),                  #
                ("select", imp.C_EXTENSION),                    #
                ("errno", imp.C_BUILTIN),                       #
                ("murmurhash", imp.PKG_DIRECTORY),              # requirements
                ("murmurhash.about", imp.PY_COMPILED),          #
                ("murmurhash.mrmr", imp.C_EXTENSION),           #
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

                        if actual_type in [imp.C_BUILTIN, imp.PKG_DIRECTORY]:
                            self.assertIsNone(file)
                            self.assertEqual("", suffix)
                            self.assertEqual("", mode)
                        else:
                            data = file.read()
                            self.assertEqual(0, len(data))
                            if actual_type == imp.PY_SOURCE:
                                self.assertEqual("r", mode)
                                self.assertIsInstance(data, str)
                            else:
                                self.assertEqual("rb", mode)
                                self.assertIsInstance(data, bytes)
                            self.assertPredicate(str.endswith, pathname, suffix)

                        # See comment about torchvision in find_module_override.
                        if actual_type == imp.C_EXTENSION:
                            self.assertPredicate(exists, pathname)

                        mod = imp.load_module(prefix, file, pathname, description)
                        self.assertEqual(prefix, mod.__name__)
                        self.assertEqual(actual_type == imp.PKG_DIRECTORY,
                                         hasattr(mod, "__path__"))
                        self.assertIsNotNone(mod.__spec__)
                        self.assertEqual(mod.__name__, mod.__spec__.name)

                        if actual_type == imp.C_BUILTIN:
                            self.assertIsNone(pathname)
                        elif actual_type == imp.PKG_DIRECTORY:
                            self.assertEqual(pathname, dirname(mod.__file__))
                        else:
                            self.assertEqual(re.sub(r"\.pyc$", ".py", pathname),
                                             re.sub(r"\.pyc$", ".py", mod.__file__))

                        if i < len(words) - 1:
                            self.assertEqual(imp.PKG_DIRECTORY, actual_type)
                            prefix += "."
                            path = mod.__path__
                        else:
                            self.assertEqual(expected_type, actual_type)

    # This trick was used by Electron Cash to load modules under a different name. The Electron
    # Cash Android app no longer needs it, but there may be other software which does.
    def test_imp_rename(self):
        # Clean start to allow test to be run more than once.
        for name in list(sys.modules):
            if name.startswith("imp_rename"):
                del sys.modules[name]

        # Renames in stdlib are not currently supported.
        with self.assertRaisesRegex(ImportError, "ChaquopyZipImporter does not support "
                                    "loading module 'json' under a different name 'jason'"):
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
        # its package. Despite this, it can still be imported under its new name using `from
        # ... import`. This seems to contradict the documentation of __import__, but it's not
        # important enough to investigate just now.
        self.assertFalse(hasattr(imp_rename_2, "mod_3"))

    # Make sure the standard library importer implements the new loader API
    # (https://stackoverflow.com/questions/63574951).
    def test_zipimport(self):
        for mod_name in ["zipfile",  # Imported during bootstrap
                         "wave"]:    # Imported after bootstrap
            with self.subTest(mod_name=mod_name):
                old_mod = import_module(mod_name)
                spec = importlib.util.find_spec(mod_name)
                new_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(new_mod)

                self.assertIsNot(new_mod, old_mod)
                for attr_name in ["__name__", "__file__"]:
                    with self.subTest(attr_name=attr_name):
                        self.assertEqual(getattr(new_mod, attr_name),
                                         getattr(old_mod, attr_name))

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

    def test_pr_distributions(self):
        import pkg_resources as pr
        self.assertCountEqual(REQUIREMENTS, [dist.project_name for dist in pr.working_set])
        self.assertEqual("0.28.0", pr.get_distribution("murmurhash").version)

    def test_pr_resources(self):
        import pkg_resources as pr

        # App ZIP
        pkg = "android1"
        names = ["subdir", "__init__.py", "a.txt", "b.so", "mod1.py"]
        self.assertCountEqual(names, pr.resource_listdir(pkg, ""))
        for name in names:
            with self.subTest(name=name):
                self.assertTrue(pr.resource_exists(pkg, name))
                self.assertEqual(pr.resource_isdir(pkg, name),
                                 name == "subdir")
        self.assertFalse(pr.resource_exists(pkg, "nonexistent"))
        self.assertFalse(pr.resource_isdir(pkg, "nonexistent"))

        self.assertCountEqual(["c.txt"], pr.resource_listdir(pkg, "subdir"))
        self.assertTrue(pr.resource_exists(pkg, "subdir/c.txt"))
        self.assertFalse(pr.resource_isdir(pkg, "subdir/c.txt"))
        self.assertFalse(pr.resource_exists(pkg, "subdir/nonexistent.txt"))

        self.check_pr_resource(APP_ZIP, pkg, "__init__.py", b"# This package is")
        self.check_pr_resource(APP_ZIP, pkg, "a.txt", b"alpha\n")
        self.check_pr_resource(APP_ZIP, pkg, "b.so", b"bravo\n")
        self.check_pr_resource(APP_ZIP, pkg, "subdir/c.txt", b"charlie\n")

        # Requirements ZIP
        self.reset_package("murmurhash")
        self.assertCountEqual(["include", "tests", "__init__.pxd", "__init__.pyc", "about.pyc",
                               "mrmr.pxd", "mrmr.pyx", "mrmr.so"],
                              pr.resource_listdir("murmurhash", ""))
        self.assertCountEqual(["MurmurHash2.h", "MurmurHash3.h"],
                              pr.resource_listdir("murmurhash", "include/murmurhash"))

        self.check_pr_resource(REQS_COMMON_ZIP, "murmurhash", "__init__.pyc", MAGIC_NUMBER)
        self.check_pr_resource(REQS_COMMON_ZIP, "murmurhash", "mrmr.pxd", b"from libc.stdint")
        self.check_pr_resource(REQS_ABI_ZIP, "murmurhash", "mrmr.so", b"\x7fELF")

    def check_pr_resource(self, zip_name, package, filename, start):
        import pkg_resources as pr
        with self.subTest(package=package, filename=filename):
            data = pr.resource_string(package, filename)
            self.assertPredicate(data.startswith, start)

            abs_filename = pr.resource_filename(package, filename)
            self.assertEqual(asset_path(zip_name, package.replace(".", "/"), filename),
                             abs_filename)
            if splitext(filename)[1] in [".py", ".pyc", ".so"]:
                # Importable files are not extracted.
                self.assertNotPredicate(exists, abs_filename)
            else:
                with open(abs_filename, "rb") as f:
                    self.assertEqual(data, f.read())

    def reset_package(self, package_name):
        package = import_module(package_name)
        for entry in package.__path__:
            rmtree(entry)
        self.clean_reload(package)

    def test_spec_from_file_location(self):
        # This is the recommended way to load a module from a known filename
        # (https://docs.python.org/3.8/library/importlib.html#importing-a-source-file-directly).
        def import_from_filename(name, location):
            spec = importlib.util.spec_from_file_location(name, location)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module

        for name, zip_name, zip_path, attr in [
                ("module1", APP_ZIP, "module1.py", "test_relative"),
                ("module1_renamed", APP_ZIP, "module1.py", "test_relative"),
                ("android1", APP_ZIP, "android1/__init__.py", "x"),
                ("murmurhash", REQS_COMMON_ZIP, "murmurhash/__init__.py", "get_include"),
                ("murmurhash.about", REQS_COMMON_ZIP, "murmurhash/about.py", "__license__")]:
            with self.subTest(name=name):
                module = import_from_filename(name, asset_path(zip_name, zip_path))
                self.assertEqual(name, module.__name__)
                self.assertTrue(hasattr(module, attr))

        bad_path = asset_path(APP_ZIP, "nonexistent.py")
        with self.assertRaisesRegex(FileNotFoundError, bad_path):
            import_from_filename("nonexistent", bad_path)

    # Unlike pkg_resources, importlib.resources cannot access subdirectories within packages.
    def test_importlib_resources(self):
        # App ZIP
        pkg = "android1"
        names = ["subdir", "__init__.py", "a.txt", "b.so", "mod1.py"]
        self.assertCountEqual(names, resources.contents(pkg))
        for name in names:
            with self.subTest(name=name):
                self.assertEqual(resources.is_resource(pkg, name),
                                 name != "subdir")

        self.check_ir_resource(APP_ZIP, pkg, "__init__.py", b"# This package is")
        self.check_ir_resource(APP_ZIP, pkg, "a.txt", b"alpha\n")
        self.check_ir_resource(APP_ZIP, pkg, "b.so", b"bravo\n")

        self.assertFalse(resources.is_resource(pkg, "invalid.py"))
        with self.assertRaisesRegex(FileNotFoundError, "invalid.py"):
            resources.read_binary(pkg, "invalid.py")
        with self.assertRaisesRegex(FileNotFoundError, "invalid.py"):
            with resources.path(pkg, "invalid.py"):
                pass

        # Requirements ZIP
        self.reset_package("murmurhash")
        self.assertCountEqual(["include", "tests", "__init__.pxd", "__init__.pyc", "about.pyc",
                               "mrmr.pxd", "mrmr.pyx", "mrmr.so"],
                              resources.contents("murmurhash"))

        self.check_ir_resource(REQS_COMMON_ZIP, "murmurhash", "__init__.pyc", MAGIC_NUMBER)
        self.check_ir_resource(REQS_COMMON_ZIP, "murmurhash", "mrmr.pxd", b"from libc.stdint")
        self.check_ir_resource(REQS_ABI_ZIP, "murmurhash", "mrmr.so", b"\x7fELF")

    def check_ir_resource(self, zip_name, package, filename, start):
        with self.subTest(package=package, filename=filename):
            data = resources.read_binary(package, filename)
            self.assertPredicate(data.startswith, start)

            with resources.path(package, filename) as abs_path:
                if splitext(filename)[1] in [".py", ".pyc", ".so"]:
                    # Importable files are not extracted.
                    self.assertEqual(join(str(context.getCacheDir()), "chaquopy/tmp"),
                                     dirname(abs_path))
                else:
                    self.assertEqual(asset_path(zip_name, package.replace(".", "/"), filename),
                                     str(abs_path))
                with open(abs_path, "rb") as f:
                    self.assertEqual(data, f.read())

    def test_importlib_metadata(self):
        dists = list(metadata.distributions())
        self.assertCountEqual(REQUIREMENTS, [d.metadata["Name"] for d in dists])
        for dist in dists:
            dist_info = str(dist._path)
            self.assertPredicate(str.startswith, dist_info, asset_path(REQS_COMMON_ZIP))
            self.assertPredicate(str.endswith, dist_info, ".dist-info")

            # .dist-info directories shouldn't be extracted.
            self.assertNotPredicate(exists, dist_info)

        dist = metadata.distribution("murmurhash")
        self.assertEqual("0.28.0", dist.version)
        self.assertEqual(dist.version, dist.metadata["Version"])
        self.assertIsNone(dist.files)
        self.assertEqual("Matthew Honnibal", dist.metadata["Author"])
        self.assertEqual(["chaquopy-libcxx (>=7000)"], dist.requires)

    @contextmanager
    def assertModifies(self, filename):
        TEST_MTIME = calendar.timegm((2020, 1, 2, 3, 4, 5))
        os.utime(filename, (TEST_MTIME, TEST_MTIME))
        self.assertEqual(TEST_MTIME, os.stat(filename).st_mtime)
        yield
        self.assertNotEqual(TEST_MTIME, os.stat(filename).st_mtime)

    @contextmanager
    def assertNotModifies(self, filename):
        before_stat = os.stat(filename)
        os.chmod(filename, before_stat.st_mode & ~0o222)
        try:
            yield
            after_stat = os.stat(filename)
            self.assertEqual(before_stat.st_mtime, after_stat.st_mtime)
            self.assertEqual(before_stat.st_ino, after_stat.st_ino)
        finally:
            os.chmod(filename, before_stat.st_mode)


# On Android, getDeclaredMethods and getDeclaredFields fail when the member's type refers to a
# class that cannot be loaded. Test the partial workaround in Reflector.
class TestAndroidReflect(AndroidTestCase):

    MEMBERS = ["tcFieldPublic", "tcFieldProtected", "tcMethodPublic", "tcMethodProtected",
               "iFieldPublic", "iFieldProtected", "iMethodPublic", "iMethodProtected",
               "finalize"]

    def test_android_reflect(self):
        from com.chaquo.python.demo import TestAndroidReflect as TAR

        if API_LEVEL >= 26:
            # TextClassifier is in the platform, so all members should be visible.
            self.assertMembers(TAR, self.MEMBERS)
        elif API_LEVEL >= 21:
            # Overridden methods should be visible, plus public methods that don't involve
            # TextClassifier.
            self.assertMembers(TAR, ["iMethodPublic", "finalize"])
        else:
            # Only overridden methods should be visible.
            self.assertMembers(TAR, ["finalize"])

    def assertMembers(self, cls, names):
        for name in names:
            with self.subTest(name=name):
                self.assertTrue(self.declares_member(cls, name))

        for name in self.MEMBERS:
            if name not in names:
                with self.subTest(name=name):
                    self.assertFalse(self.declares_member(cls, name))

    def declares_member(self, cls, name):
        hasattr(cls, name)  # Adds member to __dict__ if it exists.
        return name in cls.__dict__


class TestAndroidStdlib(AndroidTestCase):

    def test_ctypes(self):
        import ctypes
        from ctypes.util import find_library

        def assertHasSymbol(dll, name):
            self.assertIsNotNone(getattr(dll, name))
        def assertNotHasSymbol(dll, name):
            with self.assertRaises(AttributeError):
                getattr(dll, name)

        # Library extraction caused by CDLL.
        from murmurhash import mrmr
        os.remove(mrmr.__file__)
        ctypes.CDLL(mrmr.__file__)
        self.assertPredicate(exists, mrmr.__file__)

        # Library extraction caused by find_library.
        os.remove(LIBCXX_FILENAME)
        find_library_result = find_library("c++_shared")
        self.assertIsInstance(find_library_result, str)

        # This test covers non-Python libraries: for Python modules, see pyzmq/test.py.
        if (platform.architecture()[0] == "64bit") and (API_LEVEL < 23):
            self.assertNotIn("/", find_library_result)
        else:
            self.assertEqual(LIBCXX_FILENAME, find_library_result)

        # Whether find_library returned an absolute filename or not, the file should have been
        # extracted and the return value should be accepted by CDLL.
        self.assertPredicate(exists, LIBCXX_FILENAME)
        libcxx = ctypes.CDLL(find_library_result)
        assertHasSymbol(libcxx, "_ZSt9terminatev")  # std::terminate()
        assertNotHasSymbol(libcxx, "nonexistent")

        # System libraries.
        self.assertIsNotNone(find_library("c"))
        self.assertIsNotNone(find_library("log"))
        self.assertIsNone(find_library("nonexistent"))

        libc = ctypes.CDLL(find_library("c"))
        liblog = ctypes.CDLL(find_library("log"))
        assertHasSymbol(libc, "printf")
        assertHasSymbol(liblog, "__android_log_write")
        assertNotHasSymbol(libc, "__android_log_write")

        # Global search (https://bugs.python.org/issue34592): only works on newer API levels.
        if API_LEVEL >= 21:
            main = ctypes.CDLL(None)
            assertHasSymbol(main, "printf")
            assertHasSymbol(main, "__android_log_write")
            assertNotHasSymbol(main, "nonexistent")

        assertHasSymbol(ctypes.pythonapi, "PyObject_Str")

    def test_datetime(self):
        import datetime
        # This is the interface to the native _datetime module, which is required by NumPy. The
        # attribute will only exist if _datetime was available when datetime was first
        # imported.
        self.assertTrue(datetime.datetime_CAPI)

    def test_json(self):
        from json import encoder, scanner
        # These attributes will be None if the native _json module was unavailable when json
        # was first imported, which would significantly reduce the module's performance.
        self.assertTrue(encoder.c_make_encoder)
        self.assertTrue(scanner.c_make_scanner)

    def test_lib2to3(self):
        # Requires grammar files to be available in stdlib zip.
        from lib2to3 import pygram  # noqa: F401

    def test_hashlib(self):
        import hashlib
        INPUT = b"The quick brown fox jumps over the lazy dog"
        TESTS = [
            # OpenSSL and built-in, OpenSSL preferred.
            ("sha1", "2fd4e1c67a2d28fced849ee1bb76e7391b93eb12"),

            # OpenSSL and built-in, built-in preferred.
            ("sha3_512", ("01dedd5de4ef14642445ba5f5b97c15e47b9ad931326e4b0727cd94cefc44fff23f"
                          "07bf543139939b49128caf436dc1bdee54fcb24023a08d9403f9b4bf0d450")),
            ("blake2b", ("a8add4bdddfd93e4877d2746e62817b116364a1fa7bc148d95090bc7333b3673f8240"
                         "1cf7aa2e4cb1ecd90296e3f14cb5413f8ed77be73045b13914cdcd6a918")),

            # OpenSSL only.
            ("ripemd160", "37f332f68db77bd9d7edd4969571ad671cf9dd3b"),
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

    def test_multiprocessing(self):
        from multiprocessing.dummy import Pool
        import random
        import time

        def square_slowly(x):
            time.sleep(random.uniform(0.1, 0.2))
            return x ** 2

        with Pool(8) as pool:
            start = time.time()
            self.assertEqual([0, 1, 4, 9, 16, 25, 36, 49],
                             pool.map(square_slowly, range(8), chunksize=1))
            duration = time.time() - start
            self.assertGreater(duration, 0.1)
            self.assertLess(duration, 0.25)

        from multiprocessing import get_context, synchronize
        ctx = get_context()
        for name in ["Barrier", "BoundedSemaphore", "Condition", "Event", "Lock", "RLock",
                     "Semaphore"]:
            cls = getattr(synchronize, name)
            with self.assertRaisesRegex(OSError, "This platform lacks a functioning sem_open"):
                if name == "Barrier":
                    cls(1, ctx=ctx)
                else:
                    cls(ctx=ctx)

    def test_os(self):
        self.assertEqual("posix", os.name)
        self.assertTrue(os.access(os.environ["HOME"], os.R_OK | os.W_OK | os.X_OK))

        self.assertTrue(os.get_exec_path())
        for name in os.get_exec_path():
            with self.subTest(name=name):
                self.assertTrue(os.access(name, os.X_OK))

    def test_pickle(self):
        import pickle
        # This attribute will only exist if the native _pickle module was available when
        # pickle was first imported.
        self.assertTrue(pickle.PickleBuffer)

    def test_platform(self):
        # Requires sys.executable to exist.
        import platform
        p = platform.platform()
        self.assertRegex(p, r"^Linux")

    def test_select(self):
        import select
        self.assertFalse(hasattr(select, "kevent"))
        self.assertFalse(hasattr(select, "kqueue"))

        import selectors
        self.assertIs(selectors.DefaultSelector, selectors.EpollSelector)

    def test_signal(self):
        import enum
        import signal

        # These functions may be unavailable if _signal was compiled incorrectly.
        for name in ["pthread_sigmask", "sigpending", "sigwait", "valid_signals"]:
            with self.subTest(name=name):
                self.assertTrue(hasattr(signal, name))

        vs = signal.valid_signals()
        self.assertIsInstance(vs, set)
        vs = list(vs)

        self.assertEqual(1, vs[0])
        self.assertIs(signal.SIGHUP, vs[0])
        self.assertIsInstance(vs[0], signal.Signals)
        self.assertIsInstance(vs[0], enum.IntEnum)
        self.assertEqual("<Signals.SIGHUP: 1>", repr(vs[0]))

        self.assertEqual(signal.NSIG - 1, vs[-1])
        self.assertEqual(signal.NSIG - 1, len(vs))

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
        self.assertRegex(resp.info()["Content-type"], r"^text/html")

    def test_subprocess(self):
        # An executable on the PATH.
        subprocess.run(["ls", os.environ["HOME"]])

        # A nonexistent executable.
        for name in ["nonexistent",                 # PATH search
                     "/system/bin/nonexistent"]:    # Absolute filename
            with self.subTest(name=name), self.assertRaises(FileNotFoundError):
                subprocess.run([name])

    def test_sys(self):
        self.assertEqual(ABI_FLAGS, sys.abiflags)
        self.assertEqual([""], sys.argv)
        self.assertTrue(exists(sys.executable), sys.executable)
        self.assertEqual("siphash24", sys.hash_info.algorithm)

        chaquopy_dir = f"{context.getFilesDir()}/chaquopy"
        self.assertEqual(
            [join(realpath(chaquopy_dir), path) for path in
             ["AssetFinder/app", "AssetFinder/requirements", f"AssetFinder/stdlib-{ABI}"]] +
            [join(chaquopy_dir, path) for path in
             ["stdlib-common.imy", "bootstrap.imy", f"bootstrap-native/{ABI}"]],
            sys.path)
        for p in sys.path:
            self.assertTrue(exists(p), p)

        self.assertRegex(sys.platform, r"^linux")
        self.assertRegex(sys.version,  # Make sure we don't have any "-dirty" caption.
                         r"^{}.{}.{} \(default, ".format(*sys.version_info[:3]))

    def test_sysconfig(self):
        import distutils.sysconfig
        import sysconfig
        ldlibrary = "libpython{}.{}{}.so".format(*sys.version_info[:2], ABI_FLAGS)
        self.assertEqual(ldlibrary, sysconfig.get_config_vars()["LDLIBRARY"])
        self.assertEqual(ldlibrary, distutils.sysconfig.get_config_vars()["LDLIBRARY"])

    def test_tempfile(self):
        import tempfile
        expected_dir = join(str(context.getCacheDir()), "chaquopy/tmp")
        self.assertEqual(expected_dir, tempfile.gettempdir())
        with tempfile.NamedTemporaryFile() as f:
            self.assertEqual(expected_dir, dirname(f.name))

    def test_time(self):
        import time
        t = time.gmtime(1582917965)
        self.assertEqual("Fri, 28 Feb 2020 19:26:05",
                         time.strftime("%a, %d %b %Y %H:%M:%S", t))


class TestAndroidStreams(AndroidTestCase):

    maxDiff = None

    def setUp(self):
        from android.util import Log
        Log.i(*self.get_marker())
        self.expected_log = []

    def expect_log(self, level, stream_name, lines):
        for line in lines:
            self.expected_log.append(f"{level}/python.{stream_name}: {line}")

    def tearDown(self):
        actual_log = None
        marker = "I/{}: {}".format(*self.get_marker())
        for line in subprocess.run(["logcat", "-d", "-v", "tag"], capture_output=True,
                                   errors="backslashreplace").stdout.splitlines():
            if line == marker:
                actual_log = []
            elif actual_log is not None and "/python.std" in line:
                actual_log.append(line)
        self.assertEqual(self.expected_log, actual_log)

    def get_marker(self):
        cls_name, test_name = self.id().split(".")[-2:]
        return cls_name, test_name

    def test_output(self):
        for stream_name, level in [("stdout", "I"), ("stderr", "W")]:
            with self.subTest(stream=stream_name):
                stream = getattr(sys, stream_name)
                self.check_output_properties(stream)

                def write(s, lines=None):
                    self.assertEqual(len(s), stream.write(s))
                    if lines is None:
                        lines = [s]
                    self.expect_log(level, stream_name, lines)

                write("", [])
                write("a")
                write("Hello")
                write("Hello world")
                write(" ")
                write("  ")

                # The maximum line length is 4000.
                write("foobar" * 700, [("foobar" * 666) + "foob",
                                       "ar" + ("foobar" * 33)])

                # TODO #5730: max line length should be measured in bytes.
                # These are the "full-width" digits 0-9, which encode in UTF-8 as 3 bytes each.
                # write("\uff10\uff11\uff12\uff13\uff14\uff15\uff16\uff17\uff18\uff19" * 150,
                #       ["TODO"])

                # Non-ASCII text
                write("ol\u00e9")  # Spanish
                write("\u4e2d\u6587")  # Chinese

                # Non-BMP emoji
                write("\U0001f600", [r"\xed\xa0\xbd\xed\xb8\x80" if API_LEVEL < 23
                                     else "\U0001f600"])

                # Null characters are logged using "modified UTF-8".
                write("\u0000", [r"\xc0\x80"])
                write("a\u0000", [r"a\xc0\x80"])
                write("\u0000b", [r"\xc0\x80b"])
                write("a\u0000b", [r"a\xc0\x80b"])

                # Multi-line messages. Avoid identical consecutive lines, as they may activate
                # "chatty" filtering and break the tests. Empty lines are dropped by logcat, so
                # they should be logged as a single space.
                write("\n", [" "])
                write("\na", [" ", "a"])
                write("\na\n", [" ", "a"])
                write("b\n", ["b"])
                write("c\n\n", ["c", " "])
                write("d\ne", ["d", "e"])
                write("f\n\ng", ["f", " ", "g"])

                for obj in [b"", b"hello", None, 42]:
                    with self.subTest(obj=obj):
                        with self.assertRaisesRegex(TypeError, fr"write\(\) argument must be "
                                                    fr"str, not {type(obj).__name__}"):
                            stream.write(obj)

    def test_output_bytes(self):
        for stream_name, level in [("stdout", "I"), ("stderr", "W")]:
            with self.subTest(stream=stream_name):
                stream = getattr(sys, stream_name).buffer
                self.check_output_properties(stream)

                def write(b, lines=None):
                    self.assertEqual(len(b), stream.write(b))
                    if lines is None:
                        lines = [b.decode()]
                    self.expect_log(level, stream_name, lines)

                write(b"", [])
                write(b"a")
                write(b"Hello")
                write(b"Hello world")
                write(b" ")
                write(b"  ")

                # Non-ASCII text
                write(b"ol\xc3\xa9")  # Spanish
                write(b"\xe4\xb8\xad\xe6\x96\x87")  # Chinese

                # Non-BMP emoji
                write(b"\xf0\x9f\x98\x80", [r"\xed\xa0\xbd\xed\xb8\x80" if API_LEVEL < 23
                                            else "\U0001f600"])

                # Invalid UTF-8
                write(b"\xff", [r"\xff"])
                write(b"a\xff", [r"a\xff"])
                write(b"\xffb", [r"\xffb"])
                write(b"a\xffb", [r"a\xffb"])

                # Null characters are logged using "modified UTF-8".
                write(b"\x00", [r"\xc0\x80"])
                write(b"a\x00", [r"a\xc0\x80"])
                write(b"\x00b", [r"\xc0\x80b"])
                write(b"a\x00b", [r"a\xc0\x80b"])

                for obj in ["", "hello"]:
                    with self.subTest(obj=obj):
                        with self.assertRaisesRegex(TypeError, r"decoding str is not supported"):
                            stream.write(obj)

                for obj in [None, 42]:
                    with self.subTest(obj=obj):
                        with self.assertRaisesRegex(TypeError, fr"decoding to str: need a bytes-"
                                                    fr"like object, {type(obj).__name__} found"):
                            stream.write(obj)

    def check_output_properties(self, stream):
        self.assertTrue(stream.writable())
        self.assertFalse(stream.readable())
        self.assertEqual("UTF-8", stream.encoding)
        self.assertEqual("backslashreplace", stream.errors)

    def test_input(self):
        self.assertTrue(sys.stdin.readable())
        self.assertFalse(sys.stdin.writable())
        self.assertEqual("", sys.stdin.read())
        self.assertEqual("", sys.stdin.read(42))
        self.assertEqual("", sys.stdin.readline())
        self.assertEqual("", sys.stdin.readline(42))
