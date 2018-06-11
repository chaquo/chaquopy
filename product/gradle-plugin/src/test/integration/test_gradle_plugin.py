# This file requires Python 3.6 or later.

from distutils.dir_util import copy_tree
import distutils.util
import hashlib
import json
import os
from os.path import abspath, dirname, join, relpath
import re
import shutil
import subprocess
import sys
from unittest import skip, skipUnless, TestCase
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED

import javaproperties
from kwonly_args import kwonly_defaults
import rsa


integration_dir = abspath(dirname(__file__))
repo_root = abspath(join(integration_dir, "../../../../.."))

sys.path.append(join(repo_root, "server/license"))
from check_ticket import check_ticket  # noqa: E402


with open(join(repo_root, "server/license/public.pem")) as pub_key_file:
    pub_key = rsa.PublicKey.load_pkcs1(pub_key_file.read(), "PEM")


class GradleTestCase(TestCase):
    longMessage = True
    maxDiff = None

    def RunGradle(self, *args, **kwargs):
        return RunGradle(self, *args, **kwargs)

    # Prints b as a multi-line string rather than a repr().
    def assertInLong(self, a, b, re=False, msg=None):
        try:
            if re:
                import re as re_mod
                self.assertRegex(b, re_mod.compile(a, re_mod.MULTILINE))
            else:
                self.assertIn(a, b)
        except self.failureException:
            msg = self._formatMessage(msg, "{}'{}' not found in:\n{}".format
                                      ("regex " if re else "", a, b))
            raise self.failureException(msg) from None

    # Each element of `files` must be either a filename, or a (filename, contents) tuple. ZIP
    # file entries representing directories are ignored, and must not be included in `files`.
    def assertZipContents(self, zip_file, files):
        self.assertEqual(sorted([f[0] if isinstance(f, tuple) else f
                                 for f in files]),
                         sorted(name for name in zip_file.namelist()
                                if not name.endswith("/")),
                         msg=zip_file.filename)
        for f in files:
            if isinstance(f, tuple):
                filename, attrs = f
                msg = join(zip_file.filename, filename)
                zip_info = zip_file.getinfo(filename)
                content_expected = attrs.pop("content", None)
                if content_expected is not None:
                    content_actual = zip_file.read(zip_info).decode("UTF-8").strip()
                    self.assertEqual(content_expected, content_actual, msg)
                for key, value in attrs.items():
                    self.assertEqual(value, getattr(zip_info, key), msg)

    def pre_check(self, apk_zip, apk_dir, kwargs):
        pass

    def post_check(self, apk_zip, apk_dir, kwargs):
        pass

    # stdlib and libs changed at this point. Anything which calls this method will be exercised
    # by PythonVersion.test_old_new.
    def post_201805(self, version):
        version_info = tuple(map(int, version.split(".")))
        return ((2, 7, 15) <= version_info < (3, 0, 0)) or (version_info >= (3, 6, 5))


class Basic(GradleTestCase):
    def test_base(self):
        self.RunGradle("base")

    def test_variant(self):
        self.RunGradle("base", "Basic/variant", variants=["red-debug", "blue-debug"])


class AndroidPlugin(GradleTestCase):
    def test_misordered(self):
        run = self.RunGradle("base", "AndroidPlugin/misordered", succeed=False)
        self.assertInLong("project.android not set", run.stderr)

    def test_old(self):
        run = self.RunGradle("base", "AndroidPlugin/old", succeed=False)
        self.assertInLong("requires Android Gradle plugin version 2.3.0", run.stderr)

    def test_untested(self):
        run = self.RunGradle("base", "AndroidPlugin/untested",
                             succeed=None)  # We don't care whether it succeeds.
        self.assertInLong("not been tested with Android Gradle plugin versions beyond 3.1.2",
                          run.stdout)


# Verify that the user can use noCompress without interfering with our use of it.
# We test both 1 and 2-argument calls because of the way the overloads are defined.
class NoCompress(GradleTestCase):
    def test_1(self):
        self.RunGradle("base", "NoCompress/nocompress_1",
                       compress_type=dict(alpha=ZIP_STORED, bravo=ZIP_DEFLATED,
                                          charlie=ZIP_DEFLATED))

    def test_2(self):
        self.RunGradle("base", "NoCompress/nocompress_2",
                       compress_type=dict(alpha=ZIP_STORED, bravo=ZIP_STORED,
                                          charlie=ZIP_DEFLATED))

    def test_assign(self):
        with self.assertRaisesRegex(AssertionError, "0 != 8 : assets/chaquopy/app.zip"):
            run = self.RunGradle("base", "NoCompress/nocompress_assign", run=False)
            run.rerun()
        self.assertInLong("Warning: aaptOptions.noCompress has been overridden", run.stdout)

    def post_check(self, apk_zip, apk_dir, kwargs):
        for filename, expected in kwargs["compress_type"].items():
            info = apk_zip.getinfo("assets/file." + filename)
            self.assertEqual(expected, info.compress_type)


class ApiLevel(GradleTestCase):
    def test_old(self):  # Also tests making a change
        run = self.RunGradle("base", "ApiLevel/minimum")
        run.apply_layers("ApiLevel/old")
        run.rerun(succeed=False)
        self.assertInLong("debug: Chaquopy requires minSdkVersion 15 or higher", run.stderr)

    def test_variant(self):
        run = self.RunGradle("base", "ApiLevel/variant", succeed=False)
        self.assertInLong("redDebug: Chaquopy requires minSdkVersion 15 or higher", run.stderr)


class PythonVersion(GradleTestCase):
    def test_change(self):
        run = self.RunGradle("base", version="2.7.14")
        run.apply_layers("PythonVersion/change")
        run.rerun(version="3.6.3")

    def test_missing(self):
        run = self.RunGradle("base", "PythonVersion/missing", succeed=False)
        self.assertInLong("debug: python.version not set", run.stderr)

    def test_invalid(self):
        run = self.RunGradle("base", "PythonVersion/invalid", succeed=False)
        self.assertInLong("debug: invalid python.version '2.7.99'. Current versions are "
                          "[2.7.15, 3.6.5].", run.stderr)

    def test_old_new(self):
        excerpt = "does not contain all current Chaquopy features and bug fixes"
        run = self.RunGradle("base", run=False)
        for old, new in [("2.7.14", "2.7.15"), ("3.6.3", "3.6.5")]:
            major = old[0]
            run.apply_layers("PythonVersion/old_" + major)
            run.rerun(version=old)
            self.assertInLong("Warning: debug: python.version {} {}. Please switch to one of "
                              "the following versions as soon as possible: [2.7.15, 3.6.5]."
                              .format(old, excerpt), run.stdout)
            run.apply_layers("PythonVersion/new_" + major)
            run.rerun(version=new)
            self.assertNotIn(excerpt, run.stdout)

    def test_variant(self):
        self.RunGradle("base", "PythonVersion/variant",
                       variants={"py2-debug": dict(version="2.7.14"),
                                 "py3-debug": dict(version="3.6.3")})

    def test_variant_merge(self):
        self.RunGradle("base", "PythonVersion/variant_merge",
                       variants={"py2-debug": dict(version="2.7.14"),
                                 "py3-debug": dict(version="3.6.3")})

    def test_variant_missing(self):
        run = self.RunGradle("base", "PythonVersion/variant_missing", succeed=False)
        self.assertInLong("missingDebug: python.version not set", run.stderr)


class AbiFilters(GradleTestCase):
    def test_missing(self):
        run = self.RunGradle("base", "AbiFilters/missing", succeed=False)
        self.assertInLong("debug: Chaquopy requires ndk.abiFilters", run.stderr)

    def test_invalid(self):
        run = self.RunGradle("base", "AbiFilters/invalid", succeed=False)
        self.assertInLong("debug: Chaquopy does not support the ABI 'armeabi'. "
                          "Supported ABIs are [armeabi-v7a, x86].", run.stderr)

    def test_variant(self):
        self.RunGradle("base", "AbiFilters/variant",
                       variants={"armeabi_v7a-debug": {"abis": ["armeabi-v7a"]},
                                 "x86-debug":         {"abis": ["x86"]}})

    def test_variant_merge(self):
        self.RunGradle("base", "AbiFilters/variant_merge",
                       variants={"x86-debug":  {"abis": ["x86"]},
                                 "both-debug": {"abis": ["armeabi-v7a", "x86"]}})

    def test_variant_missing(self):
        run = self.RunGradle("base", "AbiFilters/variant_missing", succeed=False)
        self.assertInLong("missingDebug: Chaquopy requires ndk.abiFilters", run.stderr)

    # We only test adding an ABI, because when removing one I kept getting this error: Execution
    # failed for task ':app:transformNativeLibsWithStripDebugSymbolForDebug'.
    # java.io.IOException: Failed to delete
    # ....\app\build\intermediates\transforms\stripDebugSymbol\release\folders\2000\1f\main\lib\armeabi-v7a
    # I've reported https://issuetracker.google.com/issues/62291921. Other people have had
    # similar problems, e.g. https://github.com/mrmaffen/vlc-android-sdk/issues/63.
    def test_change(self):
        run = self.RunGradle("base")
        run.apply_layers("AbiFilters/2")
        run.rerun(abis=["armeabi-v7a", "x86"])


class PythonSrc(GradleTestCase):
    def test_change(self):
        # Missing (as opposed to empty) src/main/python directory is already tested by Basic.
        #
        # Git can't track a directory hierarchy containing no files, and in this case even a
        # .gitignore file would invalidate the point of the test.
        empty_src = join(integration_dir, "data/PythonSrc/empty/app/src/main/python")
        if not os.path.isdir(empty_src):
            os.makedirs(empty_src)
        run = self.RunGradle("base", "PythonSrc/empty")

        run.apply_layers("PythonSrc/1")                                 # Add
        run.rerun(app=[("one.py", {"content": "one"}), "package/submodule.py"])
        run.apply_layers("PythonSrc/2")                                 # Modify
        run.rerun(app=[("one.py", {"content": "one modified"}), "package/submodule.py"])
        os.remove(join(run.project_dir, "app/src/main/python/one.py"))  # Remove
        run.rerun(app=["package/submodule.py"])

    def test_filter(self):
        run = self.RunGradle("base", "PythonSrc/filter_1", app=["one.py"])
        run.apply_layers("PythonSrc/filter_2")
        run.rerun(app=["two.py"])

    def test_variant(self):
        self.RunGradle(
            "base", "PythonSrc/variant",
            variants={"red-debug": dict(app=["common.py", ("color.py", {"content": "red"})]),
                      "blue-debug": dict(app=["common.py", ("color.py", {"content": "blue"})])})

    def test_conflict(self):
        variants = {"red-debug": dict(app=["common.py", ("color.py", {"content": "red"})]),
                    "blue-debug": dict(app=["common.py", ("color.py", {"content": "blue"})])}
        run = self.RunGradle("base", "PythonSrc/conflict", variants=variants, succeed=False)
        self.assertInLong('(?s)mergeBlueDebugPythonSources.*Encountered duplicate path "common.py"',
                          run.stderr, re=True)
        run.apply_layers("PythonSrc/conflict_exclude")
        run.rerun(variants=variants)
        run.apply_layers("PythonSrc/conflict_include")
        run.rerun(variants=variants)

    def test_set_dirs(self):
        self.RunGradle("base", "PythonSrc/set_dirs", app=["two.py"])

    def test_multi_dir(self):
        self.RunGradle("base", "PythonSrc/multi_dir", app=["one.py", "two.py"])

    def test_multi_dir_conflict(self):
        run = self.RunGradle("base", "PythonSrc/multi_dir_conflict", succeed=False)
        self.assertInLong('(?s)mergeDebugPythonSources.*Encountered duplicate path "one.py"',
                          run.stderr, re=True)

    def test_multi_dir_conflict_empty(self):
        self.RunGradle("base", "PythonSrc/multi_dir_conflict_empty",
                       app=["one.py", "two.py", "empty.py"])

    # Instance metaclasses are buggy (see branch "setroot-metaclass" and #5341) and inadequately
    # documented. Make absolutely sure none of our modifications leak from build to build.
    def test_metaclass_leak(self):
        run = self.RunGradle("base", "PythonSrc/metaclass_leak_1", app=["two.py"])
        run.apply_layers("PythonSrc/metaclass_leak_2")  # Non-Chaquopy project
        run.rerun(succeed=False)
        self.assertInLong("Could not find method python()", run.stderr)

    @skip("TODO #5341 setRoot not implemented")
    def test_set_root(self):
        self.RunGradle("base", "PythonSrc/set_root", app=[("one.py", {"content": "one main2"})],
                       classes=["One", "One$Main2"])


class ExtractPackages(GradleTestCase):
    def test_change(self):
        run = self.RunGradle("base", "ExtractPackages/1", extract_packages=["alpha"])
        run.apply_layers("ExtractPackages/2")
        run.rerun(extract_packages=["alpha", "bravo.subpackage", "charlie"])

    def test_variant(self):
        self.RunGradle("base", "ExtractPackages/variant",
                       variants={"red-debug": dict(extract_packages=["red"]),
                                 "blue-debug": dict(extract_packages=["blue"])})

    def test_variant_merge(self):
        self.RunGradle("base", "ExtractPackages/variant_merge",
                       variants={"red-debug": dict(extract_packages=["common"]),
                                 "blue-debug": dict(extract_packages=["common", "blue"])})


class Pyc(GradleTestCase):
    def test_change(self):
        run = self.RunGradle("base", pyc={"stdlib": True})
        run.apply_layers("Pyc/change")
        run.rerun(pyc={"stdlib": False})

    def test_variant(self):
        self.RunGradle("base", "Pyc/variant",
                       variants={"red-debug": dict(pyc={"stdlib": True}),
                                 "blue-debug": dict(pyc={"stdlib": False})})

    def test_variant_merge(self):
        self.RunGradle("base", "Pyc/variant_merge",
                       variants={"red-debug": dict(pyc={"stdlib": False}),
                                 "blue-debug": dict(pyc={"stdlib": True})})

    def post_check(self, apk_zip, apk_dir, kwargs):
        pyc = kwargs["pyc"]
        version = kwargs["version"]

        stdlib_files = set(ZipFile(join(apk_dir, "assets/chaquopy/stdlib.zip")).namelist())
        self.assertEqual(pyc["stdlib"],    "argparse.pyc" in stdlib_files)
        self.assertNotEqual(pyc["stdlib"], "argparse.py" in stdlib_files)
        if self.post_201805(version):
            # See build_stdlib.py in crystax/platform/ndk.
            for grammar_stem in ["Grammar", "PatternGrammar"]:
                self.assertIn("lib2to3/{}{}.final.0.pickle".format(grammar_stem, version),
                              stdlib_files)


class BuildPython(GradleTestCase):
    # Verify that buildPython default major version is taken from app Python major version,
    # using an sdist which installs different modules depending on sys.version.
    def test_default(self):
        self.RunGradle("base", "BuildPython/default",
                       variants={"py2-debug": {"version": "2.7.15", "requirements": ["two.py"]},
                                 "py3-debug": {"version": "3.6.5", "requirements": ["three.py"]}})

    def test_change(self):
        run = self.RunGradle("base", "BuildPython/change_1", requirements=["apple/__init__.py"])
        run.apply_layers("BuildPython/change_2")
        run.rerun(succeed=False)
        self.assertInLong("'pythoninvalid' failed to start", run.stderr)

    def test_mismatch(self):
        run = self.RunGradle("base", "BuildPython/mismatch", succeed=False)
        self.assertInLong("buildPython major version (2) does not match app Python major "
                          "version (3)", run.stderr)

    @skipUnless(os.name == "nt", "Windows-specific")
    def test_py_not_found(self):
        run = self.RunGradle("base", "BuildPython/py_not_found", succeed=False)
        self.assertInLong("'py -2.8': could not find the requested version of Python", run.stderr)

    def test_variant(self):
        run = self.RunGradle("base", "BuildPython/variant",
                             requirements=["apple/__init__.py"], variants=["good-debug"])
        run.rerun(variants=["bad-debug"], succeed=False)
        self.assertInLong("'pythoninvalid' failed to start", run.stderr)

    def test_variant_merge(self):
        run = self.RunGradle("base", "BuildPython/variant_merge", variants=["red-debug"],
                             succeed=False)
        self.assertInLong("'python-red' failed to start", run.stderr)
        run.rerun(variants=["blue-debug"], succeed=False)
        self.assertInLong("'python-blue' failed to start", run.stderr)


# Use these as mixins to run a set of tests once each for python2 and python3.
class BuildPythonCase(TestCase):
    def setUp(self):
        super(BuildPythonCase, self).setUp()
        os.environ["python_version"] = self.python_version

    def tearDown(self):
        del os.environ["python_version"]
        super(BuildPythonCase, self).tearDown()

class BuildPython2(BuildPythonCase):
    python_version = "2.7.15"

class BuildPython3(BuildPythonCase):
    python_version = "3.6.5"


class PythonReqs(GradleTestCase):
    def test_change(self):
        run = self.RunGradle("base")                               # No reqs
        run.apply_layers("PythonReqs/1a")                          # Add one req
        run.rerun(requirements=["apple/__init__.py"])
        run.apply_layers("PythonReqs/1")                           # Replace with a req which has a
        run.rerun(requirements=["alpha/__init__.py",               #   transitive dependency
                                "alpha_dep/__init__.py"])
        run.apply_layers("PythonReqs/2")                           # Add another req
        run.rerun(requirements=["alpha/__init__.py",
                                "alpha_dep/__init__.py",
                                "bravo/__init__.py"])
        run.apply_layers("base")                                   # Remove all
        run.rerun()

    def test_download(self):
        self.RunGradle("base", "PythonReqs/download", abis=["armeabi-v7a", "x86"],
                       requirements={"common": ["_regex_core.py", "regex.py", "test_regex.py",
                                                "six.py"],
                                     "armeabi-v7a": ["_regex.so"], "x86": ["_regex.so"]})

    def test_install_variant(self):
        self.RunGradle("base", "PythonReqs/install_variant",
                       variants={"red-debug":  {"requirements": ["apple/__init__.py"]},
                                 "blue-debug": {"requirements": ["bravo/__init__.py"]}})

    def test_install_variant_merge(self):
        self.RunGradle("base", "PythonReqs/install_variant_merge",
                       variants={"red-debug":  {"requirements": ["apple/__init__.py"]},
                                 "blue-debug": {"requirements": ["apple/__init__.py",
                                                                 "bravo/__init__.py"]}})

    def test_options_variant(self):
        self.RunGradle("base", "PythonReqs/options_variant",
                       variants={"red-debug":  {"requirements": ["apple/__init__.py"]},
                                 "blue-debug": {"requirements": ["apple_local/__init__.py"]}})

    def test_options_variant_merge(self):
        self.RunGradle("base", "PythonReqs/options_variant_merge",
                       variants={"red-debug":  {"requirements": ["alpha/__init__.py",
                                                                 "alpha_dep/__init__.py"]},
                                 "blue-debug": {"requirements": ["alpha/__init__.py"]}})

    def test_reqs_file(self):
        run = self.RunGradle("base", "PythonReqs/reqs_file",
                             requirements=["apple/__init__.py", "bravo/__init__.py"])
        run.apply_layers("PythonReqs/reqs_file_2")
        run.rerun(requirements=["alpha/__init__.py", "alpha_dep/__init__.py",
                                "bravo/__init__.py"])

    def test_wheel_file(self):
        run = self.RunGradle("base", "PythonReqs/wheel_file", requirements=["apple/__init__.py"])
        run.apply_layers("PythonReqs/wheel_file_2")
        run.rerun(requirements=["apple2/__init__.py"])

    def test_sdist_file(self):
        self.RunGradle("base", "PythonReqs/sdist_file", requirements=["alpha_dep/__init__.py"])

    def test_sdist_native(self):
        run = self.RunGradle("base", run=False)
        for name in ["sdist_native_ext", "sdist_native_clib", "sdist_native_compiler"]:
            with self.subTest(name=name):
                run.apply_layers(f"PythonReqs/{name}")
                run.rerun(succeed=False)
                self.assertInLong("Chaquopy cannot compile native code", run.stdout)
                url = fr"file:.*app/{name}-1.0.tar.gz"
                if name == "sdist_native_compiler":
                    # This test fails at the egg_info stage, so the name and version are
                    # unavailable.
                    req_str = url
                else:
                    # The other tests fail at the bdist_wheel stage, so the name and version
                    # have been obtained from egg_info.
                    req_str = f"{name.replace('_', '-')}==1.0 from {url}"
                self.assertInLong(fr"Failed to install {req_str}." +
                                  self.tracker_advice() + r"$", run.stderr, re=True)

    def test_editable(self):
        run = self.RunGradle("base", "PythonReqs/editable", succeed=False)
        self.assertInLong("Invalid python.pip.install format: '-e src'", run.stderr)

    def test_wheel_index(self):
        # If testing on another platform, add it to the list below, and add corresponding
        # wheels to packages/dist.
        self.assertIn(distutils.util.get_platform(), ["linux-x86_64", "win-amd64"])

        # This test has build platform wheels for version 0.2, and an Android wheel for version
        # 0.1, to test that pip always picks the target platform, not the workstation platform.
        run = self.RunGradle("base", "PythonReqs/wheel_index_1",
                             requirements=["native1_android_15_x86/__init__.py"])

        # This test only has build platform wheels.
        run.apply_layers("PythonReqs/wheel_index_2")
        run.rerun(succeed=False)
        self.assertInLong("No matching distribution found for native2", run.stderr)

    # Even though this is now a standard pip feature, we should still test it because we've
    # modified the index preference order.
    def test_wheel_build_tag(self):
        self.RunGradle("base", "PythonReqs/build_tag",
                       requirements=["build2/__init__.py"])

    def test_mixed_index(self):
        # This package has an sdist for version 2.0, compatible wheels for version 1.0 and
        # 1.3, and an incompatible wheel for version 1.6.
        run = self.RunGradle("base", "PythonReqs/mixed_index_1",
                             requirements=[("native3_android_15_x86/__init__.py",
                                            {"content": "# Version 1.3"})])
        self.assertInLong("Using version 1.3 (newest version is 2.0, but Chaquopy prefers "
                          "wheels over sdists", run.stdout)

        # Now we force version 2.0 to be selected, but it will fail at the egg_info stage.
        # (Failure at later stages is covered by test_sdist_native.)
        run.apply_layers("PythonReqs/mixed_index_2")
        run.rerun(succeed=False)
        self.assertInLong(r"Failed to install native3==2.0 from "
                          r"file:.*dist/native3-2.0.tar.gz." + self.tracker_advice() +
                          self.wheel_advice("1.0", "1.3") + r"$",
                          run.stderr, re=True)

    def test_no_binary_fail(self):
        # This is the same as mixed_index_2, except the wheels are excluded from consideration
        # using --no-binary, so the wheel advice won't appear.
        run = self.RunGradle("base", "PythonReqs/no_binary_fail", succeed=False)
        self.assertInLong(r"Failed to install native3 from file:.*dist/native3-2.0.tar.gz." +
                          self.tracker_advice() + r"$",
                          run.stderr, re=True)

    def test_no_binary_succeed(self):
        self.RunGradle("base", "PythonReqs/no_binary_succeed",
                       requirements=["no_binary_sdist/__init__.py"])

    def test_sdist_index(self):
        # This test has only an sdist, which will fail at the egg_info stage as in
        # test_mixed_index.
        run = self.RunGradle("base", "PythonReqs/sdist_index", succeed=False)
        self.assertInLong(r"Failed to install native4 from file:.*dist/native4-0.2.tar.gz." +
                          self.tracker_advice() + r"$",
                          run.stderr, re=True)

    def test_multi_abi(self):
        # This is not the same as the filename pattern used in our real wheels, but the point
        # is to test that the multi-ABI packaging works correctly.
        self.RunGradle(
            "base", "PythonReqs/multi_abi_1", abis=["armeabi-v7a", "x86"],
            requirements={"common": ["apple/__init__.py",  # Pure Python requirement.

                                     # Same filenames, same content in both ABIs. (Same
                                     # filenames with different content is covered by
                                     # test_multi_abi_clash below.)
                                     "common/__init__.py",
                                     "pkg/__init__.py"],

                          # Different filenames in both ABIs.
                          "armeabi-v7a": ["module_armeabi_v7a.pyd",
                                          "pkg/submodule_armeabi_v7a.pyd"],
                          "x86": ["module_x86.pyd",
                                  "pkg/submodule_x86.pyd"]})

    def test_multi_abi_variant(self):
        variants = {"armeabi_v7a-debug": {"abis": ["armeabi-v7a"],
                                          "requirements": ["apple/__init__.py",
                                                           "common/__init__.py",
                                                           "module_armeabi_v7a.pyd",
                                                           "pkg/__init__.py",
                                                           "pkg/submodule_armeabi_v7a.pyd"]},
                    "x86-debug":         {"abis": ["x86"],
                                          "requirements": ["apple/__init__.py",
                                                           "common/__init__.py",
                                                           "module_x86.pyd",
                                                           "pkg/__init__.py",
                                                           "pkg/submodule_x86.pyd"]}}
        self.RunGradle("base", "PythonReqs/multi_abi_variant", variants=variants)

    def test_multi_abi_clash(self):
        # Timestamps matter because the runtime uses them to decide whether to re-extract
        # things. The zipfile module returns the timestamps as given below, with no timezone
        # adjustment, but Windows Explorer's ZIP viewer may adjust the displayed timestamp
        # depending on the current timezone and DST.
        self.RunGradle(
            "base", "PythonReqs/multi_abi_clash", abis=["armeabi-v7a", "x86"],
            requirements={"common": [],
                          "armeabi-v7a": [("multi_abi_1_armeabi_v7a.pyd",
                                           {"date_time": (2017, 12, 9, 14, 29, 30)}),
                                          ("multi_abi_1_pure/__init__.py",
                                           {"content": "# Clashing module (armeabi-v7a copy)",
                                            "date_time": (2017, 12, 9, 14, 27, 48)})],
                          "x86": [("multi_abi_1_x86.pyd",
                                   {"date_time": (2017, 12, 9, 14, 29, 24)}),
                                  ("multi_abi_1_pure/__init__.py",
                                   {"content": "# Clashing module (x86 copy)",
                                    "date_time": (2017, 12, 9, 14, 28, 12)})]})

    # ABIs should be installed in alphabetical order. (In the order specified is not possible
    # because the Android Gradle plugin keeps abiFilters in a HashSet.)
    def test_multi_abi_order(self):
        # armeabi-v7a will install a pure-Python wheel, so the requirement will not be
        # installed again for x86, even though an x86 wheel is available.
        run = self.RunGradle("base", "PythonReqs/multi_abi_order_1", abis=["armeabi-v7a", "x86"],
                             requirements=["multi_abi_order_pure/__init__.py"])

        # armeabi-v7a will install a native wheel, so the requirement will be installed again
        # for x86, which will select the pure-Python wheel.
        run.apply_layers("PythonReqs/multi_abi_order_2")
        run.rerun(abis=["armeabi-v7a", "x86"],
                  requirements={"common": [],
                                "armeabi-v7a": ["multi_abi_order_armeabi_v7a.pyd"],
                                "x86": ["multi_abi_order_pure/__init__.py"]})

    def test_file_clash_identical(self):
        self.RunGradle("base", "PythonReqs/file_clash_identical",
                       requirements=["dir_clash/a.py", "dir_clash/b.py",
                                     "dir_clash/file_clash.py"])

    def test_file_clash_different(self):
        run = self.RunGradle("base", "PythonReqs/file_clash_different", succeed=False)
        self.assertInLong("Found multiple different copies of " +
                          join("dir_clash", "file_clash.py"), run.stderr)

    def tracker_advice(self):
        return (" For assistance, please raise an issue at "
                "https://github.com/chaquo/chaquopy/issues.")

    def wheel_advice(self, *versions):
        return (r" Or try using one of the following versions, which are available as pre-built "
                r"wheels: \[{}\].".format(", ".join("'{}'".format(v) for v in versions)))


class PythonReqs2(PythonReqs, BuildPython2):
    pass
class PythonReqs3(PythonReqs, BuildPython3):
    pass
del PythonReqs


class StaticProxy(GradleTestCase):
    reqs = ["chaquopy_test/__init__.py", "chaquopy_test/a.py", "chaquopy_test/b.py"]

    def test_change(self):
        run = self.RunGradle("base", "StaticProxy/reqs", requirements=self.reqs,
                             classes=["a.ReqsA1", "b.ReqsB1"])
        app = ["chaquopy_test/__init__.py", "chaquopy_test/a.py"]
        run.apply_layers("StaticProxy/src_1")       # Src should take priority over reqs.
        run.rerun(requirements=self.reqs, app=app, classes=["a.SrcA1", "b.ReqsB1"])
        run.apply_layers("StaticProxy/src_only")    # Change staticProxy setting
        run.rerun(app=app, requirements=self.reqs, classes=["a.SrcA1"])
        run.apply_layers("StaticProxy/src_2")       # Change source code
        run.rerun(app=app, requirements=self.reqs, classes=["a.SrcA2"])
        run.apply_layers("base")                    # Remove all
        run.rerun(app=app)

    def test_variant(self):
        self.RunGradle("base", "StaticProxy/variant",
                       requirements=self.reqs,
                       variants={"red-debug":  {"classes": ["a.ReqsA1"]},
                                 "blue-debug": {"classes": ["b.ReqsB1"]}})

    def test_variant_merge(self):
        self.RunGradle("base", "StaticProxy/variant_merge",
                       requirements=self.reqs,
                       variants={"red-debug":  {"classes": ["a.ReqsA1"]},
                                 "blue-debug": {"classes": ["a.ReqsA1", "b.ReqsB1"]}})

class StaticProxy2(StaticProxy, BuildPython2):
    pass
class StaticProxy3(StaticProxy, BuildPython3):
    pass
del StaticProxy


class License(GradleTestCase):
    def test_app_key(self):
        DEMO_KEY = "BBfoCXBWFxWgyFaO8ATfwievD0WqRKCPiz1WgCzhifWV"
        DEMO3_KEY = "BNzb-z7UV1drJRdiO-6OVvrcUUPRYp7WL7n_Lzp-0vbz"

        run = self.RunGradle("base", "License/demo")

        run.apply_key(DEMO_KEY)
        run.rerun(licensed_id="com.chaquo.python.demo")

        run.apply_key(DEMO3_KEY)
        run.rerun(succeed=False)
        self.assertInLong("Chaquopy license verification failed", run.stderr)

        run.apply_layers("License/demo3")
        run.rerun(licensed_id="com.chaquo.python.demo3")

        # Before 2.0.0, a single-app license was indicated by an empty key, but that is now
        # interpreted as meaning "no license".
        run.apply_key("")
        run.rerun(licensed_id=None)

        run.apply_key(None)
        run.rerun(licensed_id=None)

    def test_standard_key(self):
        run = self.RunGradle("base")

        run.apply_key("invalid")
        run.rerun(succeed=False)
        self.assertInLong("Chaquopy license verification failed", run.stderr)

        run.apply_key("AU5-6D8smj5fE6b53i9P7czOLV1L4Gf8W1L6RB_qkOQr")
        run.rerun(licensed_id="com.chaquo.python.test")

        run.apply_key(None)
        run.rerun(licensed_id=None)

    def test_stolen_ticket(self):
        with self.assertRaisesRegex(AssertionError,
                                    "ValueError: License is for 'com.chaquo.python.demo', "
                                    "but this app is 'com.chaquo.python.test'"):
            self.RunGradle("base", licensed_id="com.chaquo.python.test",
                           bad_ticket=join(integration_dir,
                                           "data/License/tickets/demo.txt"))

    def test_invalid_ticket(self):
        with self.assertRaisesRegex(AssertionError, "VerificationError: Verification failed"):
            self.RunGradle("base", licensed_id="com.chaquo.python.test",
                           bad_ticket=join(integration_dir,
                                           "data/License/tickets/invalid.txt"))

    def pre_check(self, apk_zip, apk_dir, kwargs):
        bad_ticket = kwargs.get("bad_ticket")
        if bad_ticket:
            asset_dir = join(apk_dir, "assets/chaquopy")
            shutil.copy(bad_ticket, join(asset_dir, "ticket.txt"))
            build_json_filename = join(asset_dir, "build.json")
            with open(build_json_filename) as build_json_file:
                build_json = json.load(build_json_file)
            build_json["assets"]["ticket.txt"] = asset_hash(bad_ticket)
            with open(build_json_filename, "w") as build_json_file:
                json.dump(build_json, build_json_file)


class RunGradle(object):
    @kwonly_defaults
    def __init__(self, test, run=True, key=None, *layers, **kwargs):
        self.test = test
        self.agp_version = os.environ["AGP_VERSION"]

        module, cls, func = re.search(r"^(\w+)\.(\w+)\.test_(\w+)$", test.id()).groups()
        self.run_dir = join(repo_root, "product/gradle-plugin/build/test/integration",
                            self.agp_version, cls, func)
        if os.path.exists(self.run_dir):
            rmtree(self.run_dir)

        self.project_dir = join(self.run_dir, "project")
        os.makedirs(self.project_dir)
        self.apply_layers(*layers)
        self.apply_key(key)
        if run:
            self.rerun(**kwargs)

    def apply_layers(self, *layers):
        for layer in layers:
            copy_tree(join(integration_dir, "data", layer), self.project_dir,
                      preserve_times=False)  # https://github.com/gradle/gradle/issues/2301
            if layer == "base":
                self.apply_layers("base-" + self.agp_version)

    def apply_key(self, key):
        LP_FILENAME = "local.properties"
        with open(join(repo_root, "product", LP_FILENAME)) as in_file, \
             open(join(self.project_dir, LP_FILENAME), "w") as out_file:  # noqa: E127
            for line in in_file:
                if "chaquopy.license" not in line:
                    out_file.write(line)
            if key is not None:
                print("\nchaquopy.license=" + key, file=out_file)

    @kwonly_defaults
    def rerun(self, succeed=True, variants=["debug"], **kwargs):
        # "version" is also used in Pyc.post_check.
        #
        # TODO: edit test files to replace as many explicit Python version numbers as possible
        # with an environment variable, as we already have in BuildPythonCase subclasses.
        for k, v in [("version", getattr(self.test, "python_version", "2.7.14"))]:
            kwargs.setdefault(k, v)

        status, self.stdout, self.stderr = self.run_gradle(variants)
        if status == 0:
            if succeed is False:  # (succeed is None) means we don't care
                self.dump_run("run unexpectedly succeeded")

            for variant in variants:
                outputs_apk_dir = join(self.project_dir, "app/build/outputs/apk")
                apk_filename = join(outputs_apk_dir,
                                    "app-{}.apk".format(variant))       # Android plugin 2.x
                if not os.path.isfile(apk_filename):
                    apk_filename = join(outputs_apk_dir, variant.replace("-", "/"),
                                        "app-{}.apk".format(variant))   # Android plugin 3.x

                apk_zip = ZipFile(apk_filename)
                apk_dir = join(self.run_dir, "apk", variant)
                if os.path.exists(apk_dir):
                    rmtree(apk_dir)
                os.makedirs(apk_dir)
                apk_zip.extractall(apk_dir)

                merged_kwargs = kwargs.copy()
                if isinstance(variants, dict):
                    merged_kwargs.update(variants[variant])
                try:
                    self.check_apk(apk_zip, apk_dir, **merged_kwargs)
                except Exception as e:
                    self.dump_run(f"check_apk failed: {type(e).__name__}: {e}")

            # Run a second time to check all tasks are considered up to date.
            first_msg = "\n=== FIRST RUN STDOUT ===\n" + self.stdout
            status, second_stdout, second_stderr = self.run_gradle(variants)
            if status != 0:
                self.stdout, self.stderr = second_stdout, second_stderr
                self.dump_run("Second run: exit status {}".format(status))
            self.test.assertInLong(":app:extractPythonBuildPackages UP-TO-DATE", second_stdout,
                                   msg=first_msg)
            for variant in variants:
                for verb, obj in [("generate", "AppAssets"), ("generate", "BuildAssets"),
                                  ("generate", "JniLibs"),  ("generate", "LicenseAssets"),
                                  ("generate", "MiscAssets"), ("generate", "Proxies"),
                                  ("generate", "Requirements"), ("generate", "RequirementsAssets")]:
                    msg = task_name(verb, variant, "Python" + obj) + " UP-TO-DATE"
                    self.test.assertInLong(msg, second_stdout, msg=first_msg)

        else:
            if succeed:
                self.dump_run("exit status {}".format(status))

    def run_gradle(self, variants):
        os.chdir(self.project_dir)
        os.environ["integration_dir"] = integration_dir
        # --info explains why tasks were not considered up to date.
        # --console plain prevents output being truncated by a "String index out of range: -1"
        #   error on Windows.
        gradlew = "gradlew.bat" if sys.platform.startswith("win") else "./gradlew"
        process = subprocess.Popen([gradlew, "--stacktrace", "--info", "--console", "plain"] +
                                   [task_name("assemble", v) for v in variants],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   universal_newlines=True)
        stdout, stderr = process.communicate()
        return process.wait(), stdout, stderr

    # TODO: refactor this into a set of independent methods, all using the same API as pre_check and
    # post_check. See also `setdefault` loop at top of rerun().
    @kwonly_defaults
    def check_apk(self, apk_zip, apk_dir, abis=["x86"], classes=[], app=[],
                  requirements=[], extract_packages=[], licensed_id=None, **kwargs):
        kwargs = KwargsWrapper(kwargs)
        self.test.pre_check(apk_zip, apk_dir, kwargs)

        # All ZIP assets should be stored uncompressed, whether top-level or not.
        for info in apk_zip.infolist():
            if re.search(r"^assets/chaquopy/.*\.zip$", info.filename):
                self.test.assertEqual(ZIP_STORED, info.compress_type, info.filename)

        # Top-level assets
        asset_dir = join(apk_dir, "assets/chaquopy")
        reqs_suffixes = sorted(["common"] + abis)
        self.test.assertEqual(["app.zip", "bootstrap-native", "bootstrap.zip", "build.json",
                               "cacert.pem"] +
                              ["requirements-{}.zip".format(suffix) for suffix in reqs_suffixes] +
                              ["stdlib-native", "stdlib.zip", "ticket.txt"],
                              sorted(os.listdir(asset_dir)))

        # Python source
        app_zip = ZipFile(join(asset_dir, "app.zip"))
        self.test.assertZipContents(app_zip, app)

        # Python requirements
        for suffix in reqs_suffixes:
            if isinstance(requirements, dict):
                files = requirements[suffix]
            else:
                if suffix == "common":
                    files = requirements
                else:
                    files = []
            reqs_zip = ZipFile(join(asset_dir, "requirements-{}.zip".format(suffix)))
            self.test.assertZipContents(reqs_zip, files)

        # Python bootstrap
        bootstrap_native_dir = join(asset_dir, "bootstrap-native")
        self.test.assertEqual(sorted(abis), sorted(os.listdir(bootstrap_native_dir)))
        for abi in abis:
            self.test.assertEqual(["_ctypes.so", "java", "select.so"],
                                  sorted(os.listdir(join(bootstrap_native_dir, abi))))
            self.test.assertEqual(["__init__.py", "chaquopy.so"],
                                  sorted(os.listdir(join(bootstrap_native_dir, abi, "java"))))

        # Python stdlib
        version = kwargs["version"]
        stdlib_native_dir = join(asset_dir, "stdlib-native")
        self.test.assertEqual([abi + ".zip" for abi in sorted(abis)],
                              sorted(os.listdir(stdlib_native_dir)))
        for abi in abis:
            stdlib_native_zip = ZipFile(join(stdlib_native_dir, abi + ".zip"))
            expected_modules = ["_multiprocessing.so", "_socket.so", "_sqlite3.so",
                                "_ssl.so", "pyexpat.so", "unicodedata.so"]
            if self.test.post_201805(version):
                expected_modules.append("_hashlib.so")
            self.test.assertEqual(sorted(expected_modules),
                                  sorted(stdlib_native_zip.namelist()))

        # libs
        self.test.assertEqual(sorted(abis), sorted(os.listdir(join(apk_dir, "lib"))))
        ver_suffix = version.rpartition(".")[0]
        if ver_suffix.startswith("3"):
            ver_suffix += "m"
        for abi in abis:
            libs = ["libchaquopy_java.so", "libcrystax.so",
                    "libpython{}.so".format(ver_suffix)]
            if self.test.post_201805(version):
                libs += ["libcrypto_chaquopy.so", "libssl_chaquopy.so", "libsqlite3.so"]
            self.test.assertEqual(sorted(libs),
                                  sorted(os.listdir(join(apk_dir, "lib", abi))))

        # Chaquopy runtime library
        actual_classes = dex_classes(join(apk_dir, "classes.dex"))
        self.test.assertIn("com.chaquo.python.Python", actual_classes)

        # App Java classes
        self.test.assertEqual(sorted(("chaquopy_test." + c) for c in classes),
                              sorted(c for c in actual_classes if c.startswith("chaquopy_test")))

        # build.json
        DEFAULT_EXTRACT_PACKAGES = ["certifi", "sklearn.datasets"]
        with open(join(asset_dir, "build.json")) as build_json_file:
            build_json = json.load(build_json_file)
        self.test.assertEqual(["assets", "extractPackages", "version"], sorted(build_json))
        self.test.assertEqual(version, build_json["version"])
        self.test.assertEqual(sorted(extract_packages + DEFAULT_EXTRACT_PACKAGES),
                              sorted(build_json["extractPackages"]))
        asset_list = []
        for dirpath, dirnames, filenames in os.walk(asset_dir):
            asset_list += [relpath(join(dirpath, f), asset_dir).replace("\\", "/")
                           for f in filenames]
        self.test.assertEqual(
            {filename: asset_hash(join(asset_dir, filename))
             for filename in asset_list if filename != "build.json"},
            build_json["assets"])

        # Licensing
        ticket_filename = join(asset_dir, "ticket.txt")
        if licensed_id:
            with open(ticket_filename) as ticket_file:
                check_ticket(ticket_file.read(), pub_key, licensed_id)
        else:
            self.test.assertEqual(os.stat(ticket_filename).st_size, 0)

        self.test.post_check(apk_zip, apk_dir, kwargs)
        self.test.assertFalse(kwargs.unused_kwargs)

    def dump_run(self, msg):
        self.test.fail(msg + "\n" +
                       "=== STDOUT ===\n" + self.stdout +
                       "=== STDERR ===\n" + self.stderr)


def asset_hash(filename):
    with open(filename, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()


class KwargsWrapper(object):
    def __init__(self, kwargs):
        self.kwargs = kwargs
        self.unused_kwargs = set(kwargs)

    def get(self, key, default=None):
        self.unused_kwargs.discard(key)
        return self.kwargs.get(key, default)

    def __getitem__(self, key):
        self.unused_kwargs.discard(key)
        return self.kwargs[key]


def dex_classes(dex_filename):
    # The following properties file should be created manually. It's also used in
    # runtime/build.gradle.
    with open(join(repo_root, "product/local.properties")) as props_file:
        props = javaproperties.load(props_file)
    build_tools_dir = join(props["sdk.dir"], "build-tools")
    newest_ver = sorted(os.listdir(build_tools_dir))[-1]
    dexdump = subprocess.check_output([join(build_tools_dir, newest_ver, "dexdump"),
                                       dex_filename], universal_newlines=True)
    classes = []
    for line in dexdump.splitlines():
        match = re.search(r"Class descriptor *: *'L(.*);'", line)
        if match:
            classes.append(match.group(1).replace("/", "."))
    return classes


def task_name(prefix, variant, suffix=""):
    # Differs from str.capitalize() because it only affects the first character
    def cap_first(s):
        return s if (s == "") else (s[0].upper() + s[1:])

    return (":app:" + prefix +
            "".join(cap_first(word) for word in variant.split("-")) +
            cap_first(suffix))


# shutil.rmtree is unreliable on MSYS2: it frequently fails with Windows error 145 (directory
# not empty), even though it has already removed everything from that directory.
def rmtree(path):
    subprocess.check_call(["rm", "-rf", path])
