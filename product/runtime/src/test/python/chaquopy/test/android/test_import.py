import calendar
from contextlib import contextmanager
import ctypes
from ctypes.util import find_library
from importlib import import_module, metadata, reload, resources
import importlib.util
from importlib.util import cache_from_source, MAGIC_NUMBER
import io
import marshal
import os
from os.path import dirname, exists, join, realpath, relpath, splitext
from pathlib import Path, PosixPath
import pkgutil
import re
from shutil import rmtree
import sys
from traceback import format_exc
from unittest import skipIf
import types
from warnings import catch_warnings, filterwarnings
import zipfile

from java.android import importer

from ..test_utils import FilterWarningsCase
from . import ABI, context


REQUIREMENTS = ["chaquopy-libcxx", "murmurhash", "Pygments", "extract-packages"]

# REQS_COMMON_ZIP and REQS_ABI_ZIP are now both extracted into the same directory, but we
# maintain the distinction in the tests in case that changes again in the future.
APP_ZIP = "app"
REQS_COMMON_ZIP = "requirements-common"
multi_abi = len([name for name in context.getAssets().list("chaquopy")
                 if name.startswith("requirements")]) > 2
REQS_ABI_ZIP = f"requirements-{ABI}" if multi_abi else REQS_COMMON_ZIP

def asset_path(zip_name, *paths):
    return join(realpath(context.getFilesDir().toString()), "chaquopy/AssetFinder",
                zip_name.partition("-")[0], *paths)

def resource_path(zip_name, package, filename):
    return asset_path(zip_name, package.replace(".", "/"), filename)


def importable(filename):
    return splitext(filename)[1] in [".py", ".pyc", ".so"]


class TestAndroidImport(FilterWarningsCase):

    maxDiff = None

    def test_bootstrap(self):
        chaquopy_dir = join(str(context.getFilesDir()), "chaquopy")
        self.assertCountEqual(["AssetFinder", "bootstrap-native", "bootstrap.imy",
                               "cacert.pem", "stdlib-common.imy"],
                              os.listdir(chaquopy_dir))
        bn_dir = f"{chaquopy_dir}/bootstrap-native"
        self.assertCountEqual([ABI], os.listdir(bn_dir))

        stdlib_bootstrap_expected = {
            # For why each of these modules is needed, see BOOTSTRAP_NATIVE_STDLIB in
            # PythonTasks.kt.
            "java", "_bz2.so", "_ctypes.so", "_datetime.so", "_lzma.so",
            "_random.so", "_sha512.so", "_struct.so", "binascii.so", "math.so",
            "mmap.so", "zlib.so",
        }
        if sys.version_info >= (3, 12):
            stdlib_bootstrap_expected -= {"_sha512.so"}
            stdlib_bootstrap_expected |= {"_sha2.so"}
        if sys.version_info >= (3, 13):
            stdlib_bootstrap_expected -= {"_sha2.so"}
            stdlib_bootstrap_expected |= {"_opcode.so"}

        for subdir, entries in [
            (ABI, list(stdlib_bootstrap_expected)),
            (f"{ABI}/java", ["chaquopy.so"]),
        ]:
            with self.subTest(subdir=subdir):
                # Create a stray file which should be removed on the next startup.
                pid_txt = f"{os.getpid()}.txt"
                with open(f"{bn_dir}/{subdir}/{pid_txt}", "w"):
                    pass
                self.assertCountEqual(entries + [pid_txt], os.listdir(f"{bn_dir}/{subdir}"))

                # If any of the bootstrap modules haven't been imported, that means they
                # no longer need to be in the bootstrap.
                if subdir == ABI:
                    for filename in entries:
                        with self.subTest(filename=filename):
                            self.assertIn(filename.replace(".so", ""), sys.modules)

    def test_init(self):
        self.check_py("murmurhash", REQS_COMMON_ZIP, "murmurhash/__init__.py", "get_include",
                      is_package=True)
        self.check_py("android1", APP_ZIP, "android1/__init__.py", "x",
                      source_head="# This package is used by TestAndroidImport.", is_package=True)

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

    def test_ctypes(self):
        def assertHasSymbol(dll, name):
            self.assertIsNotNone(getattr(dll, name))
        def assertNotHasSymbol(dll, name):
            with self.assertRaises(AttributeError):
                getattr(dll, name)

        # Library extraction from calling CDLL with a path outside of chaquopy/lib.
        from murmurhash import mrmr
        os.remove(mrmr.__file__)
        ctypes.CDLL(mrmr.__file__)
        self.assertPredicate(exists, mrmr.__file__)

        # Library extraction caused by find_library.
        LIBCXX_FILENAME = asset_path(REQS_ABI_ZIP, "chaquopy/lib/libc++_shared.so")
        os.remove(LIBCXX_FILENAME)
        self.assertEqual(find_library("c++_shared"), LIBCXX_FILENAME)
        self.assertPredicate(exists, LIBCXX_FILENAME)
        libcxx = ctypes.CDLL(LIBCXX_FILENAME)
        assertHasSymbol(libcxx, "_ZSt9terminatev")  # std::terminate()
        assertNotHasSymbol(libcxx, "nonexistent")

        # Calling CDLL with a basename in chaquopy/lib can also cause an extraction.
        os.remove(LIBCXX_FILENAME)
        ctypes.CDLL("libc++_shared.so")
        self.assertPredicate(exists, LIBCXX_FILENAME)

        # CDLL with nonexistent filenames, both relative and absolute.
        for name in ["invalid.so", f"{dirname(mrmr.__file__)}/invalid.so"]:
            with self.assertRaisesRegex(OSError, "invalid.so"):
                ctypes.CDLL(name)

        # System libraries.
        self.assertEqual(find_library("c"), "libc.so")
        self.assertEqual(find_library("log"), "liblog.so")
        self.assertIsNone(find_library("nonexistent"))

        libc = ctypes.CDLL(find_library("c"))
        liblog = ctypes.CDLL(find_library("log"))
        assertHasSymbol(libc, "printf")
        assertHasSymbol(liblog, "__android_log_write")
        assertNotHasSymbol(libc, "__android_log_write")

        # Global search (https://bugs.python.org/issue34592)
        main = ctypes.CDLL(None)
        assertHasSymbol(main, "printf")
        assertHasSymbol(main, "__android_log_write")
        assertNotHasSymbol(main, "nonexistent")

        # pythonapi
        assertHasSymbol(ctypes.pythonapi, "PyObject_Str")

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
        self.reset_package("murmurhash")
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
        mod = import_module(package)
        data = pkgutil.get_data(package, filename)
        self.assertTrue(data.startswith(start))

        if importable(filename):
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

    def test_extract_packages(self):
        self.check_extract_packages("ep_alpha", [])
        self.check_extract_packages("ep_bravo", [
            "__init__.py", "mod.py", "one/__init__.py", "two/__init__.py"
        ])
        self.check_extract_packages("ep_charlie", ["one/__init__.py"])

        # If a module has both a .py and a .pyc file, the .pyc file should be used because
        # it'll load faster.
        import ep_bravo
        py_path = asset_path(REQS_COMMON_ZIP, "ep_bravo/__init__.py")
        self.assertEqual(py_path, ep_bravo.__file__)
        self.assertEqual(py_path + "c", ep_bravo.__spec__.origin)

    def check_extract_packages(self, package, files):
        mod = import_module(package)
        cache_dir = asset_path(REQS_COMMON_ZIP, package)
        self.assertEqual(cache_dir, dirname(mod.__file__))
        if exists(cache_dir):
            rmtree(cache_dir)

        self.clean_reload(mod)
        if not files:
            self.assertNotPredicate(exists, cache_dir)
        else:
            self.assertCountEqual(files,
                                  [relpath(join(dirpath, name), cache_dir)
                                   for dirpath, _, filenames in os.walk(cache_dir)
                                   for name in filenames])
            for path in files:
                with open(f"{cache_dir}/{path}") as file:
                    self.assertEqual(f"# This file is {package}/{path}\n", file.read())

    def clean_reload(self, mod):
        sys.modules.pop(mod.__name__, None)
        submod_names = [name for name in sys.modules if name.startswith(mod.__name__ + ".")]
        for name in submod_names:
            sys.modules.pop(name)

        # For extension modules, this may reuse the same module object (see create_dynamic
        # in import.c).
        return import_module(mod.__name__)

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

        # When importlib._bootstrap._init_module_attrs is passed an already-initialized
        # module with override=False, it sets __spec__ and leaves the other attributes
        # alone. So if the module object was reused in clean_reload, then __loader__ and
        # __spec__.loader may be equal but not identical.
        spec = mod.__spec__
        self.assertEqual(mod_name, spec.name)
        self.assertEqual(loader, spec.loader)

        expected_origin = filename
        if filename.startswith(asset_path(REQS_COMMON_ZIP)) and filename.endswith(".py"):
            expected_origin += "c"
        self.assertEqual(spec.origin, expected_origin)

        # Loader methods (get_data is tested elsewhere)
        self.assertEqual(is_package, loader.is_package(mod_name))
        self.assertIsInstance(loader.get_code(mod_name),
                              types.CodeType if filename.endswith(".py") else type(None))

        source = loader.get_source(mod_name)
        if source_head:
            self.assertTrue(source.startswith(source_head), repr(source))
        else:
            self.assertIsNone(source)

        self.assertEqual(loader.get_filename(mod_name), expected_origin)

        return mod

    # Verify that the traceback builder can get source code from the loader in all contexts.
    # (The "package1" test files are also used in TestImport.)
    def test_exception(self):
        col_marker = r'( +[~^]+\n)?'  # Column marker (Python >= 3.11)
        test_frame = (
            fr'  File "{asset_path(APP_ZIP)}/chaquopy/test/android/test_import.py", '
            fr'line \d+, in test_exception\n'
            fr'    .+?\n'  # Source code line from this file
            + col_marker)
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
                fr'        \^(\^\^)?\n'
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
                col_marker +
                fr'  File "{asset_path(APP_ZIP)}/package1/other_error.py", '
                fr'line 1, in <module>\n'
                fr'    int\("hello"\)\n' +
                col_marker +
                r"ValueError: invalid literal for int\(\) with base 10: 'hello'\n$")
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
                fr"NameError: name '__file__' is not defined")
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

    @skipIf(sys.version_info >= (3, 12), "imp was removed in Python 3.12")
    def test_imp(self):
        import imp

        with catch_warnings():
            filterwarnings("default", category=DeprecationWarning)

            with self.assertRaisesRegex(ImportError, "No module named 'nonexistent'"):
                imp.find_module("nonexistent")

            # See comment about torchvision below.
            from murmurhash import mrmr
            os.remove(mrmr.__file__)

            # If any of the below modules already exist, they will be reloaded. This may have
            # side-effects, e.g. if we'd included sys, then sys.executable would be reset and
            # test_sys below would fail.
            for mod_name, expected_type in [
                    ("dbm", imp.PKG_DIRECTORY),                     # stdlib
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

    # This trick was used by Electron Cash to load modules under a different name. The
    # Electron Cash Android app no longer needs it, but there may be other software
    # which does.
    @skipIf(sys.version_info >= (3, 12), "imp was removed in Python 3.12")
    def test_imp_rename(self):
        import imp

        with catch_warnings():
            filterwarnings("default", category=DeprecationWarning)

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

    # Ensure that a package can be imported by a bare name when it's in an AssetFinder subdirectory.
    # This is typically done when vendoring packages and dynamically adjusting sys.path. See #820.
    def test_path_subdir(self):
        sys.modules.pop("tests", None)
        murmur_path = asset_path(REQS_COMMON_ZIP, "murmurhash")
        tests_path = join(murmur_path, "tests/__init__.py")
        sys.path.insert(0, murmur_path)
        try:
            import tests
        finally:
            sys.path.remove(murmur_path)
        self.assertEqual(tests_path, tests.__file__)

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

        # Check that a non-existent package returns an empty list.
        for path in ("somemissingpackage", "some/missing/package"):
            mod_infos = list(pkgutil.iter_modules([f"{murmurhash.__path__[0]}/{path}"]))
            self.assertEqual([], mod_infos)

    def test_pr_metadata(self):
        with catch_warnings():
            filterwarnings("default", category=DeprecationWarning)
            import pkg_resources as pr

        self.assertCountEqual(REQUIREMENTS, [dist.project_name for dist in pr.working_set])
        self.assertEqual("0.28.0", pr.get_distribution("murmurhash").version)

    def test_pr_resources(self):
        with catch_warnings():
            filterwarnings("default", category=DeprecationWarning)
            import pkg_resources as pr

        # App ZIP
        pkg = "android1"
        names = ["subdir", "__init__.py", "a.txt", "b.so", "mod1.py"]
        self.check_pr_resource_dir(pkg, "", names)
        for name in names:
            with self.subTest(name=name):
                self.assertTrue(pr.resource_exists(pkg, name))
                self.assertEqual(pr.resource_isdir(pkg, name),
                                 name == "subdir")

        self.check_pr_resource_dir(pkg, "subdir", ["c.txt"])

        self.check_pr_resource(APP_ZIP, pkg, "__init__.py", b"# This package is")
        self.check_pr_resource(APP_ZIP, pkg, "a.txt", b"alpha\n")
        self.check_pr_resource(APP_ZIP, pkg, "b.so", b"bravo\n")
        self.check_pr_resource(APP_ZIP, pkg, "subdir/c.txt", b"charlie\n")

        for filename in ["invalid.py", "subdir/nonexistent.txt"]:
            with self.subTest(filename=filename):
                self.assertFalse(pr.resource_exists(pkg, filename))
                self.assertFalse(pr.resource_isdir(pkg, filename))

                with self.assertRaisesRegex(FileNotFoundError, filename):
                    pr.resource_listdir(pkg, filename)
                with self.assertRaisesRegex(FileNotFoundError, filename):
                    pr.resource_string(pkg, filename)
                with self.assertRaisesRegex(FileNotFoundError, filename):
                    pr.resource_stream(pkg, filename)
                with self.assertRaisesRegex(FileNotFoundError, filename):
                    pr.resource_filename(pkg, filename)

        # Requirements ZIP
        pkg = "murmurhash"
        self.reset_package(pkg)
        self.assertCountEqual(
            pr.resource_listdir(pkg, ""),
            ["include", "tests", "__init__.pxd", "__init__.pyc", "about.pyc",
             "mrmr.pxd", "mrmr.pyx", "mrmr.so"])
        self.check_pr_resource_dir(pkg, "include", ["murmurhash"])
        self.check_pr_resource_dir(
            pkg, "include/murmurhash",
            ["MurmurHash2.h", "MurmurHash3.h"])

        self.check_pr_resource(REQS_COMMON_ZIP, pkg, "__init__.pyc", MAGIC_NUMBER)
        self.check_pr_resource(REQS_COMMON_ZIP, pkg, "mrmr.pxd", b"from libc.stdint")
        self.check_pr_resource(
            REQS_COMMON_ZIP, pkg, "include/murmurhash/MurmurHash2.h",
            b"//-----------------------------------------------------------------------------\n"
            b"// MurmurHash2 was written by Austin Appleby")
        self.check_pr_resource(REQS_ABI_ZIP, pkg, "mrmr.so", b"\x7fELF")

    def check_pr_resource_dir(self, package, filename, children):
        import pkg_resources as pr

        self.assertTrue(pr.resource_exists(package, filename))
        self.assertTrue(pr.resource_isdir(package, filename))

        with self.assertRaisesRegex(IsADirectoryError, filename):
            pr.resource_string(package, filename)

        self.assertCountEqual(pr.resource_listdir(package, filename), children)

    def check_pr_resource(self, zip_name, package, filename, start):
        import pkg_resources as pr

        with self.subTest(package=package, filename=filename):
            self.assertTrue(pr.resource_exists(package, filename))
            self.assertFalse(pr.resource_isdir(package, filename))
            with self.assertRaisesRegex(NotADirectoryError, filename):
                pr.resource_listdir(package, filename)

            data = pr.resource_string(package, filename)
            self.assertPredicate(data.startswith, start)

            with pr.resource_stream(package, filename) as file:
                self.assertIsInstance(file, io.BytesIO)
                self.assertEqual(file.read(), data)

            abs_filename = pr.resource_filename(package, filename)
            self.assertEqual(abs_filename, resource_path(zip_name, package, filename))
            if importable(filename):
                # pkg_resources has a mechanism for extracting resources to temporary
                # files, but we don't currently support it.
                self.assertNotPredicate(exists, abs_filename)
            else:
                # Extracted files can be read directly.
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

    # The original importlib.resources API was deprecated in Python 3.11, but its
    # replacement isn't available until Python 3.9.
    #
    # This API cannot access subdirectories within packages.
    def test_resources_old(self):
        with catch_warnings():
            filterwarnings("default", category=DeprecationWarning)

            # App ZIP
            pkg = "android1"
            names = ["subdir", "__init__.py", "a.txt", "b.so", "mod1.py"]
            self.assertCountEqual(resources.contents(pkg), names)
            for name in names:
                with self.subTest(name=name):
                    self.assertEqual(resources.is_resource(pkg, name),
                                     name != "subdir")

            self.check_resource_old(APP_ZIP, pkg, "__init__.py", "# This package is")
            self.check_resource_old(APP_ZIP, pkg, "a.txt", "alpha\n")
            self.check_resource_old(APP_ZIP, pkg, "b.so", "bravo\n")

            filename = "invalid.py"
            self.assertFalse(resources.is_resource(pkg, filename))
            with self.assertRaisesRegex(FileNotFoundError, filename):
                resources.read_binary(pkg, filename)
            with self.assertRaisesRegex(FileNotFoundError, filename):
                resources.open_binary(pkg, filename)
            with self.assertRaisesRegex(FileNotFoundError, filename):
                with resources.path(pkg, filename):
                    pass

            # Requirements ZIP
            pkg = "murmurhash"
            self.reset_package(pkg)
            self.assertCountEqual(
                resources.contents(pkg),
                ["include", "tests", "__init__.pxd", "__init__.pyc", "about.pyc",
                 "mrmr.pxd", "mrmr.pyx", "mrmr.so"])

            self.check_resource_old(REQS_COMMON_ZIP, pkg, "__init__.pyc", MAGIC_NUMBER)
            self.check_resource_old(REQS_COMMON_ZIP, pkg, "mrmr.pxd", "from libc.stdint")
            self.check_resource_old(REQS_ABI_ZIP, pkg, "mrmr.so", b"\x7fELF")

    def check_resource_old(self, zip_name, package, filename, start):
        with self.subTest(package=package, filename=filename):
            self.assertTrue(resources.is_resource(package, filename))

            binary = isinstance(start, bytes)
            data = getattr(
                resources, "read_binary" if binary else "read_text"
            )(package, filename)
            self.assertPredicate(data.startswith, start)

            abs_filename = resource_path(zip_name, package, filename)
            with getattr(
                resources, "open_binary" if binary else "open_text"
            )(package, filename) as file:
                self.check_resource_file(file, abs_filename, data, binary)

            with resources.path(package, filename) as path:
                self.check_resource_path(path, abs_filename, data, binary)

    def check_resource_file(self, file, abs_filename, data, binary):
        if binary:
            buffer = file
        else:
            self.assertIsInstance(file, io.TextIOWrapper)
            buffer = file.buffer

        if importable(abs_filename):
            self.assertIsInstance(buffer, io.BytesIO)
        else:
            self.assertIsInstance(buffer, io.BufferedReader)
            self.assertEqual(buffer.name, abs_filename)

        self.assertEqual(file.read(), data)

    def check_resource_path(self, path, abs_filename, data, binary):
        self.assertIs(type(path), PosixPath)
        if importable(abs_filename):
            # Non-extracted files are copied to the temporary directory.
            self.assertEqual(dirname(path),
                             join(str(context.getCacheDir()), "chaquopy/tmp"))
        else:
            # Extracted files can be read directly.
            self.assertEqual(str(path), abs_filename)

        with open(path, "rb" if binary else "r") as file:
            self.assertEqual(file.read(), data)

    @skipIf(sys.version_info < (3, 9), "resources.files was added in Python 3.9")
    def test_resources_new(self):
        # App ZIP
        pkg = "android1"
        pkg_path = resources.files(pkg)
        self.assertNotIsInstance(pkg_path, Path)

        names = ["subdir", "__init__.py", "a.txt", "b.so", "mod1.py"]
        self.check_resource_dir(pkg_path, names)
        for name in names:
            with self.subTest(name=name):
                path = pkg_path / name
                self.assertTrue(path.exists())
                self.assertEqual(path.is_dir(), name == "subdir")
                self.assertEqual(path.is_file(), name != "subdir")

        self.check_resource_dir(pkg_path / "subdir", ["c.txt"])

        self.check_resource_new(APP_ZIP, pkg, "__init__.py", "# This package is")
        self.check_resource_new(APP_ZIP, pkg, "a.txt", "alpha\n")
        self.check_resource_new(APP_ZIP, pkg, "b.so", "bravo\n")
        self.check_resource_new(APP_ZIP, pkg, "subdir/c.txt", "charlie\n")

        for filename in ["invalid.py", "subdir/nonexistent.txt"]:
            with self.subTest(filename=filename):
                path = pkg_path / filename
                self.assertNotIsInstance(path, Path)
                self.assertFalse(path.exists())
                self.assertFalse(path.is_dir())
                self.assertFalse(path.is_file())

                with self.assertRaisesRegex(FileNotFoundError, filename):
                    next(path.iterdir())
                with self.assertRaisesRegex(FileNotFoundError, filename):
                    path.read_bytes()
                with self.assertRaisesRegex(FileNotFoundError, filename):
                    path.open()
                with self.assertRaisesRegex(FileNotFoundError, filename):
                    with resources.as_file(path):
                        pass

        # Requirements ZIP
        pkg = "murmurhash"
        self.reset_package(pkg)
        pkg_path = resources.files(pkg)
        self.check_resource_dir(
            pkg_path,
            ["include", "tests", "__init__.pxd", "__init__.pyc", "about.pyc",
             "mrmr.pxd", "mrmr.pyx", "mrmr.so"])
        self.check_resource_dir(pkg_path / "include", ["murmurhash"])
        self.check_resource_dir(
            pkg_path / "include/murmurhash", ["MurmurHash2.h", "MurmurHash3.h"])

        self.check_resource_new(REQS_COMMON_ZIP, pkg, "__init__.pyc", MAGIC_NUMBER)
        self.check_resource_new(REQS_COMMON_ZIP, pkg, "mrmr.pxd", "from libc.stdint")
        self.check_resource_new(
            REQS_COMMON_ZIP, pkg, "include/murmurhash/MurmurHash2.h",
            "//-----------------------------------------------------------------------------\n"
            "// MurmurHash2 was written by Austin Appleby")
        self.check_resource_new(REQS_ABI_ZIP, pkg, "mrmr.so", b"\x7fELF")

        # Stdlib
        pkg_path = resources.files("email")
        self.assertIsInstance(pkg_path, zipfile.Path)
        self.assertTrue(pkg_path.is_dir())

        children = [child.name for child in pkg_path.iterdir()]
        self.assertIn("mime", children)
        self.assertTrue((pkg_path / "mime").is_dir())

        self.assertIn("parser.pyc", children)
        path = pkg_path / "parser.pyc"
        self.assertFalse(path.is_dir())
        self.assertPredicate(path.read_bytes().startswith, MAGIC_NUMBER)

    def check_resource_dir(self, path, children):
        self.assertTrue(path.exists())
        self.assertTrue(path.is_dir())
        self.assertFalse(path.is_file())

        with self.assertRaisesRegex(IsADirectoryError, path.name):
            path.read_bytes()

        self.assertCountEqual([child.name for child in path.iterdir()], children)

    def check_resource_new(self, zip_name, package, filename, start):
        with self.subTest(package=package, filename=filename):
            path = resources.files(package)
            for segment in filename.split("/"):
                path = path / segment

            abs_filename = resource_path(zip_name, package, filename)
            self.assertEqual(str(path), abs_filename)

            # We should get the same result when passing the whole filename at once.
            self.assertEqual(resources.files(package) / filename, path)

            if importable(filename):
                self.assertNotIsInstance(path, Path)
            else:
                self.assertIs(type(path), PosixPath)

            self.assertTrue(path.exists())
            self.assertFalse(path.is_dir())
            self.assertTrue(path.is_file())
            with self.assertRaisesRegex(NotADirectoryError, filename):
                next(path.iterdir())

            binary = isinstance(start, bytes)
            data = getattr(path, "read_bytes" if binary else "read_text")()
            self.assertPredicate(data.startswith, start)

            with path.open("rb" if binary else "r") as file:
                self.check_resource_file(file, abs_filename, data, binary)

            with resources.as_file(path) as path_as_file:
                self.check_resource_path(path_as_file, abs_filename, data, binary)

    def test_metadata(self):
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
        self.assertEqual(["chaquopy-libcxx (>=11000)"], dist.requires)

        # Distribution objects don't implement __eq__.
        def dist_attrs(dist):
            return (dist.version, dist.metadata.items())

        # Check it still works with an unreadable directory on sys.path.
        unreadable_dir = "/"  # Blocked by SELinux.
        try:
            sys.path.insert(0, unreadable_dir)
            self.assertEqual(list(map(dist_attrs, dists)),
                             list(map(dist_attrs, metadata.distributions())))
        finally:
            try:
                sys.path.remove(unreadable_dir)
            except ValueError:
                pass

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
