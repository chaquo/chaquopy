# This file requires Python 3.6 or later.

from distutils import dir_util
import distutils.util
import hashlib
import json
import os
from os.path import abspath, dirname, join, relpath
import re
import shutil
import subprocess
import sys
from unittest import skip, skipIf, skipUnless, TestCase
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED

import javaproperties
from kwonly_args import kwonly_defaults
from retrying import retry


PYTHON_VERSION = "3.6.5"
PYTHON_VERSION_SHORT = PYTHON_VERSION[:PYTHON_VERSION.rindex(".")]

integration_dir = abspath(dirname(__file__))
repo_root = abspath(join(integration_dir, "../../../../.."))

# Android Gradle Plugin version (passed from Gradle task).
agp_version = os.environ["AGP_VERSION"]


class GradleTestCase(TestCase):
    longMessage = True
    maxDiff = None

    def RunGradle(self, *args, **kwargs):
        return RunGradle(self, *args, **kwargs)

    def assertInLong(self, a, b, re=False, msg=None):
        self.assertLong(a, b, self.assertIn, self.assertRegex, "not found in", re, msg)

    def assertNotInLong(self, a, b, re=False, msg=None):
        self.assertLong(a, b, self.assertNotIn, self.assertNotRegex,
                        "unexpectedly found in", re, msg)

    # Prints b as a multi-line string rather than a repr().
    def assertLong(self, a, b, plain_assert, re_assert, failure_msg, re, msg):
        try:
            if re:
                import re as re_mod
                re_assert(b, re_mod.compile(a, re_mod.MULTILINE))
            else:
                plain_assert(a, b)
        except self.failureException:
            prefix = "regex " if re else ""
            msg = self._formatMessage(msg, f"{prefix}'{a}' {failure_msg}:\n{b}")
            raise self.failureException(msg) from None

    # Asserts that the ZIP contains exactly the given files (do not include directories). Each
    # element of `files` must be either a filename, or a (filename, dict) tuple. The dict items
    # must either be attributes of ZipInfo, or a "content" string which will be compared with
    # the UTF-8 decoded file.
    #
    # If `dist_infos` is provided, it must be a {package: version} dict, which will be compared
    # against the top-level `.dist-info` directories in the ZIP.
    def checkZip(self, zip_filename, files, dist_infos=None):
        zip_file = ZipFile(zip_filename)
        actual_files = []
        actual_dist_infos = {}
        for info in zip_file.infolist():
            self.assertEqual((1980, 2, 1, 0, 0, 0), info.date_time, msg=info.filename)
            di_match = re.match(r"(.+)-(.+).dist-info", info.filename.split("/")[0])
            if di_match:
                version = actual_dist_infos.setdefault(di_match.group(1), di_match.group(2))
                self.assertEqual(di_match.group(2), version)
            elif not info.filename.endswith("/"):
                actual_files.append(info.filename)

        self.assertCountEqual([f[0] if isinstance(f, tuple) else f for f in files],
                              actual_files, msg=zip_file.filename)
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

        if dist_infos is not None:
            self.assertEqual(dist_infos, actual_dist_infos)

    def pre_check(self, apk_zip, apk_dir, kwargs):
        pass

    def post_check(self, apk_zip, apk_dir, kwargs):
        pass


class Basic(GradleTestCase):
    def test_base(self):
        self.RunGradle("base")

    def test_variant(self):
        self.RunGradle("base", "Basic/variant", variants=["red-debug", "blue-debug"])


# Test that new versions of build-packages.zip are correctly extracted and used.
class ChaquopyPlugin(GradleTestCase):
    # Since this version, the extracted copy of build-packages.zip has been renamed to bp.zip.
    # We distinguish the old version by its inability to install sdists.
    def test_upgrade_3_0_0(self):
        run = self.RunGradle("base", "ChaquopyPlugin/upgrade_3_0_0", succeed=False)
        self.assertInLong("Chaquopy does not support sdist packages", run.stderr)
        run.apply_layers("ChaquopyPlugin/upgrade_current")
        run.rerun(requirements=["alpha_dep/__init__.py"])

    # Since this version, there has been no change in the build-packages.zip filename. We
    # distinguish the old version by it not supporting arm64-v8a.
    def test_upgrade_4_0_0(self):
        run = self.RunGradle("base", "ChaquopyPlugin/upgrade_4_0_0", succeed=False)
        self.assertInLong("Chaquopy does not support the ABI 'arm64-v8a'", run.stderr)
        run.apply_layers("ChaquopyPlugin/upgrade_current")
        run.rerun(abis=["arm64-v8a"])


class AndroidPlugin(GradleTestCase):
    ADVICE = ("please edit com.android.tools.build:gradle in the top-level build.gradle. See "
              "https://chaquo.com/chaquopy/doc/current/versions.html.")

    def test_misordered(self):
        run = self.RunGradle("base", "AndroidPlugin/misordered", succeed=False)
        self.assertInLong("project.android not set. Did you apply plugin "
                          "com.android.application before com.chaquo.python?", run.stderr)

    def test_old(self):
        run = self.RunGradle("base", "AndroidPlugin/old", succeed=False)
        self.assertInLong("This version of Chaquopy requires Android Gradle plugin version "
                          "3.1.0 or later: " + self.ADVICE, run.stderr)

    def test_untested(self):  # Also tests making a change
        run = self.RunGradle("base")
        self.assertNotInLong("not been tested with Android Gradle plugin", run.stdout)

        run.apply_layers("AndroidPlugin/untested")
        run.rerun(succeed=None)  # We don't care whether it succeeds.
        self.assertInLong("Warning: This version of Chaquopy has not been tested with Android "
                          "Gradle plugin versions beyond 3.4.0-rc02. If you experience "
                          "problems, " + self.ADVICE, run.stdout)


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
    ADVICE = "See https://chaquo.com/chaquopy/doc/current/versions.html."

    def test_minimum(self):  # Also tests making a change
        run = self.RunGradle("base", "ApiLevel/minimum")
        run.apply_layers("ApiLevel/old")
        run.rerun(succeed=False)
        self.assertInLong("debug: This version of Chaquopy requires minSdkVersion 16 or "
                          "higher. " + self.ADVICE, run.stderr)

    def test_variant(self):
        run = self.RunGradle("base", "ApiLevel/variant", succeed=False)
        self.assertInLong("redDebug: This version of Chaquopy requires minSdkVersion 16 or "
                          "higher. " + self.ADVICE, run.stderr)


class PythonVersion(GradleTestCase):
    def test_warning(self):
        run = self.RunGradle("base")
        self.assertNotInLong("python.version", run.stdout)

        run.apply_layers("PythonVersion/warning")
        run.rerun()
        self.assertInLong("Warning: Python 'version' setting is no longer required and should be "
                          "removed from build.gradle.", run.stdout)

    def test_error(self):
        run = self.RunGradle("base", "PythonVersion/error", succeed=False)
        self.assertInLong(
            f"This version of Chaquopy does not include Python version 3.6.3. "
            f"Either remove 'version' from build.gradle to use Python {PYTHON_VERSION}, or see "
            f"https://chaquo.com/chaquopy/doc/current/versions.html for other options.",
            run.stderr)


class AbiFilters(GradleTestCase):
    def test_missing(self):
        run = self.RunGradle("base", "AbiFilters/missing", succeed=False)
        self.assertInLong("debug: Chaquopy requires ndk.abiFilters", run.stderr)

    def test_invalid(self):
        run = self.RunGradle("base", "AbiFilters/invalid", succeed=False)
        self.assertInLong("debug: Chaquopy does not support the ABI 'armeabi'. "
                          "Supported ABIs are [armeabi-v7a, arm64-v8a, x86, x86_64].",
                          run.stderr)

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


def make_asset_check(test, hashes):
    def post_check(apk_zip, apk_dir, kwargs):
        for asset_path, expected_hash in hashes.items():
            test.assertEqual(expected_hash, file_sha1(f"{apk_dir}/assets/chaquopy/{asset_path}"))
    return post_check


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

    @skipIf(os.name == "posix", "For systems which don't support TZ variable")
    def test_reproducible_basic(self):
        self.post_check = make_asset_check(self, {
            "app.zip": "ace2495dbddff198cbfa9b52cbfb53bb743475dd"})
        self.RunGradle("base", "PythonSrc/1", app=["one.py", "package/submodule.py"])

    @skipUnless(os.name == "posix", "For systems which support TZ variable")
    def test_reproducible_timezone(self):
        self.post_check = make_asset_check(self, {
            "app.zip": "ace2495dbddff198cbfa9b52cbfb53bb743475dd"})

        app = ["one.py", "package/submodule.py"]
        for tz in ["UTC+0", "PST+8", "CET-1"]:  # + and - are reversed compared to normal usage.
            with self.subTest(tz=tz):
                self.RunGradle("base", "PythonSrc/1", app=app, env={"TZ": tz})

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
        stdlib_files = set(ZipFile(join(apk_dir, "assets/chaquopy/stdlib.zip")).namelist())
        self.assertEqual(pyc["stdlib"],    "argparse.pyc" in stdlib_files)
        self.assertNotEqual(pyc["stdlib"], "argparse.py" in stdlib_files)

        # See build_stdlib.py in crystax/platform/ndk.
        for grammar_stem in ["Grammar", "PatternGrammar"]:
            self.assertIn("lib2to3/{}{}.final.0.pickle".format(grammar_stem, PYTHON_VERSION),
                          stdlib_files)


class BuildPython(GradleTestCase):
    def test_change(self):
        run = self.RunGradle("base", "BuildPython/change_1", requirements=["apple/__init__.py"])
        run.apply_layers("BuildPython/change_2")
        run.rerun(succeed=False)
        self.assertInLong("'pythoninvalid' failed to start", run.stderr)

    def test_old(self):
        run = self.RunGradle("base", "BuildPython/old", succeed=False)
        self.assertInLong(r"buildPython must be version 3.4 or later: this is version 2\.7\.\d+. "
                          r"See https://chaquo.com/chaquopy/doc/current/android.html#buildpython.",
                          run.stderr, re=True)

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


class PythonReqs(GradleTestCase):
    def test_change(self):
        # No reqs.
        run = self.RunGradle("base")

        # Add one req.
        run.apply_layers("PythonReqs/1a")
        run.rerun(requirements=["apple/__init__.py"],
                  reqs_versions={"apple": "0.0.1"})

        # Replace with a req which has a transitive dependency.
        run.apply_layers("PythonReqs/1")
        run.rerun(requirements=["alpha/__init__.py", "alpha_dep/__init__.py"],
                  reqs_versions={"alpha": "0.0.1", "alpha_dep": "0.0.1"})

        # Add another req.
        run.apply_layers("PythonReqs/2")
        run.rerun(
            requirements=["alpha/__init__.py", "alpha_dep/__init__.py", "bravo/__init__.py"],
            reqs_versions={"alpha": "0.0.1", "alpha_dep": "0.0.1", "bravo": "0.0.1"})

        # Remove all.
        run.apply_layers("base")
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
        for name in ["sdist_native_ext", "sdist_native_clib", "sdist_native_compiler",
                     "sdist_native_cc"]:
            with self.subTest(name=name):
                run.apply_layers(f"PythonReqs/{name}")
                run.rerun(succeed=False)

                if name == "sdist_native_cc":
                    setup_error = "Failed to run Chaquopy_cannot_compile_native_code"
                else:
                    setup_error = "Chaquopy cannot compile native code"
                self.assertInLong(setup_error, run.stdout)

                url = fr"file:.*app/{name}-1.0.tar.gz"
                if name in ["sdist_native_compiler", "sdist_native_cc"]:
                    # These tests fail at the egg_info stage, so the name and version are
                    # unavailable.
                    req_str = url
                else:
                    # These tests fail at the bdist_wheel stage, so the name and version
                    # have been obtained from egg_info.
                    req_str = f"{name.replace('_', '-')}==1.0 from {url}"
                self.assertInLong(fr"Failed to install {req_str}." +
                                  self.tracker_advice() + r"$", run.stderr, re=True)

    def test_sdist_native_optional(self):
        run = self.RunGradle("base", run=False)
        for name in ["sdist_native_optional_ext", "sdist_native_optional_compiler"]:
            with self.subTest(name=name):
                run.apply_layers(f"PythonReqs/{name}")
                run.rerun(requirements=[f"{name}.py"])

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

    # This package has the following versions:
    #   1.0: pure wheel
    #   1.3: compatible native wheel
    #   1.6: incompatible native wheel (should be ignored)
    #   2.0: sdist
    def test_mixed_index(self):
        # With no version restriction, the compatible native wheel is preferred over the sdist,
        # despite having a lower version.
        run = self.RunGradle("base", "PythonReqs/mixed_index_1",
                             requirements=[("native3_android_15_x86/__init__.py",
                                            {"content": "# Version 1.3"})])
        self.assertInLong("Using version 1.3 (newest version is 2.0, but Chaquopy prefers "
                          "native wheels", run.stdout)

        # With "!=1.3", the sdist is selected, but it will fail at the egg_info stage.
        # (Failure at later stages is covered by test_sdist_native.)
        run.apply_layers("PythonReqs/mixed_index_2")
        run.rerun(succeed=False)
        self.assertInLong(r"Failed to install native3!=1.3 from "
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

    def test_requires_python(self):
        build_version = self.get_different_build_python_version()
        run = self.RunGradle("base", "PythonReqs/requires_python", run=False)
        with open(f"{run.project_dir}/app/index/pyver/index.html", "w") as index_file:
            def print_link(whl_version, requires_python):
                filename = f"pyver-{whl_version}-py2.py3-none-any.whl"
                print(f'<a href="{filename}" data-requires-python="=={requires_python}">'
                      f'{filename}</a><br/>', file=index_file)

            # If the build Python version is used, or the data-requires-python attribute is
            # ignored completely, then version 0.2 will be selected.
            print("<html><head></head><body>", file=index_file)
            print_link("0.1", PYTHON_VERSION)
            print_link("0.2", build_version)
            print("</body></html>", file=index_file)

        run.rerun(requirements=["pyver.py"], reqs_versions={"pyver": "0.1"})

    def test_sdist_index(self):
        # This test has only an sdist, which will fail at the egg_info stage as in
        # test_mixed_index.
        run = self.RunGradle("base", "PythonReqs/sdist_index", succeed=False)
        self.assertInLong(r"Failed to install native4 from file:.*dist/native4-0.2.tar.gz." +
                          self.tracker_advice() + r"$",
                          run.stderr, re=True)

    def test_multi_abi(self):
        # Check requirements ZIPs are reproducible.
        self.post_check = make_asset_check(self, {
            "requirements-common.zip": "498951b8a3ca3313de5f3dccf1e0b7cfa2419c6b",
            "requirements-armeabi-v7a.zip": "e71ef6f14d410f8c2339b10b16cb30424bcc57c4",
            "requirements-x86.zip": "e9a6a0d8d9e701ce4ad24c160974182e7ab0e963"})

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
        self.RunGradle(
            "base", "PythonReqs/multi_abi_clash", abis=["armeabi-v7a", "x86"],
            requirements={"common": [],
                          "armeabi-v7a": ["multi_abi_1_armeabi_v7a.pyd",
                                          ("multi_abi_1_pure/__init__.py",
                                           {"content": "# Clashing module (armeabi-v7a copy)"})],
                          "x86": ["multi_abi_1_x86.pyd",
                                  ("multi_abi_1_pure/__init__.py",
                                   {"content": "# Clashing module (x86 copy)"})]})

    # ABIs should be installed in alphabetical order. (In the order specified is not possible
    # because the Android Gradle plugin keeps abiFilters in a HashSet.)
    def test_multi_abi_order(self):
        # armeabi-v7a will install a pure-Python wheel, so the requirement will not be
        # installed again for x86, even though an x86 wheel is available.
        run = self.RunGradle("base", "PythonReqs/multi_abi_order_1", abis=["armeabi-v7a", "x86"],
                             requirements=["multi_abi_order_pure/__init__.py"],
                             reqs_versions={"multi_abi_order": "0.1"})

        # armeabi-v7a will install a native wheel, so the requirement will be installed again
        # for x86, which will select the pure-Python wheel.
        run.apply_layers("PythonReqs/multi_abi_order_2")
        run.rerun(abis=["armeabi-v7a", "x86"],
                  requirements={"common": [],
                                "armeabi-v7a": ["multi_abi_order_armeabi_v7a.pyd"],
                                "x86": ["multi_abi_order_pure/__init__.py"]},
                  reqs_versions={"multi_abi_order": "0.2"})

    def test_namespace_packages(self):
        self.RunGradle("base", "PythonReqs/namespace_packages",
                       requirements=["pkg1/a.py", "pkg1/b.py",
                                     "pkg2/a.py", "pkg2/b.py",
                                     "pkg2/pkg21/a.py", "pkg2/pkg21/b.py",
                                     "pkg3/pkg31/a.py", "pkg3/pkg31/b.py"])

    # See comment in pip_install.py. The file naming scheme is "d" for different and "i" for
    # identical content, where the things being compared are:
    #     First character: pure vs armeabi-v7a.
    #     Second character: armeabi-v7a and x86.
    #
    # All versions of dd.py are padded out to the same length to verify that the hash is being
    # checked and not just the length.
    def test_duplicate_filenames(self):
        run = self.RunGradle(
            "base", "PythonReqs/duplicate_filenames_np",  # Native, then pure.
            abis=["armeabi-v7a", "x86"],
            requirements={
                "common":       ["pkg/__init__.py", "pkg/native_only.py", "pkg/pure_only.py",
                                 ("pkg/dd.py", {"content": "# pure #############"}),
                                 ("pkg/di.py", {"content": "# pure"}),
                                 ("pkg/ii.py", {"content": "# pure, armeabi-v7a and x86"})],
                "armeabi-v7a":  ["native_armeabi_v7a.pyd",
                                 ("pkg/id.py", {"content": "# pure and armeabi-v7a"})],
                "x86":          ["native_x86.pyd",
                                 ("pkg/dd.py", {"content": "# x86 ##############"}),
                                 ("pkg/di.py", {"content": "# armeabi-v7a and x86"}),
                                 ("pkg/id.py", {"content": "# x86"})]})

        run.apply_layers("PythonReqs/duplicate_filenames_pn")  # Pure, then native.
        run.rerun(
            abis=["armeabi-v7a", "x86"],
            requirements={
                "common":       ["pkg/__init__.py", "pkg/native_only.py", "pkg/pure_only.py",
                                 ("pkg/di.py", {"content": "# armeabi-v7a and x86"}),
                                 ("pkg/ii.py", {"content": "# pure, armeabi-v7a and x86"})],
                "armeabi-v7a":  ["native_armeabi_v7a.pyd",
                                 ("pkg/dd.py", {"content": "# armeabi-v7a ######"}),
                                 ("pkg/id.py", {"content": "# pure and armeabi-v7a"})],
                "x86":          ["native_x86.pyd",
                                 ("pkg/dd.py", {"content": "# x86 ##############"}),
                                 ("pkg/id.py", {"content": "# x86"})]})

    # With a single ABI, everything should end up in common, but in two phases: first files
    # from the pure package will be moved, then all the rest. Check that this doesn't cause
    # any problems like trying to overwrite the target directory.
    #
    # This test also installs 4 additional single_file packages: one each at the beginning and
    # end of the alphabet, both before and after the duplicate_filenames packages. This
    # exercises the .dist-info processing a bit more (see commit on 2018-06-17).
    def test_duplicate_filenames_single_abi(self):
        run = self.RunGradle(
            "base", "PythonReqs/duplicate_filenames_single_abi_pn",
            requirements=["pkg/__init__.py", "pkg/native_only.py", "pkg/pure_only.py",
                          "native_x86.pyd",
                          ("pkg/dd.py", {"content": "# x86 ##############"}),
                          ("pkg/di.py", {"content": "# armeabi-v7a and x86"}),
                          ("pkg/id.py", {"content": "# x86"}),
                          ("pkg/ii.py", {"content": "# pure, armeabi-v7a and x86"}),
                          "aa_before.py", "zz_before.py", "aa_after.py", "zz_after.py"])

        run.apply_layers("PythonReqs/duplicate_filenames_single_abi_np")
        run.rerun(requirements=["pkg/__init__.py", "pkg/native_only.py", "pkg/pure_only.py",
                                "native_x86.pyd",
                                ("pkg/dd.py", {"content": "# pure #############"}),
                                ("pkg/di.py", {"content": "# pure"}),
                                ("pkg/id.py", {"content": "# pure and armeabi-v7a"}),
                                ("pkg/ii.py", {"content": "# pure, armeabi-v7a and x86"}),
                                "aa_before.py", "zz_before.py", "aa_after.py", "zz_after.py"])

    @skipIf("linux" in sys.platform, "Non-Linux build platforms only")
    def test_marker_platform(self):
        self.RunGradle("base", "PythonReqs/marker_platform", requirements=["linux.py"])

    def test_marker_python_version(self):
        run = self.RunGradle("base", "PythonReqs/marker_python_version", run=False)
        build_version = self.get_different_build_python_version()
        with open(f"{run.project_dir}/app/requirements.txt", "w") as reqs_file:
            def print_req(whl_version, python_version):
                print(f'pyver-{whl_version}-py2.py3-none-any.whl; '
                      f'python_full_version == "{python_version}"', file=reqs_file)

            # If the build Python version is used, or the environment markers are ignored
            # completely, then version 0.2 will be selected.
            print_req("0.1", PYTHON_VERSION)
            print_req("0.2", build_version)

        run.rerun(requirements=["pyver.py"], reqs_versions={"pyver": "0.1"})

    def tracker_advice(self):
        return ("\nFor assistance, please raise an issue at "
                "https://github.com/chaquo/chaquopy/issues.")

    def wheel_advice(self, *versions):
        return (r"\nOr try using one of the following versions, which are available as pre-built "
                r"wheels: \[{}\].".format(", ".join("'{}'".format(v) for v in versions)))

    def get_different_build_python_version(self):
        version = self.get_build_python_version()
        if version == PYTHON_VERSION:
            # We want to verify that packages are selected based on the target Python version,
            # not the build Python version, and we can only do that if the two versions are
            # different.
            self.skipTest(f"Build Python and target Python have the same version ({version})")
        return version

    def get_build_python_version(self):
        if os.name == "nt":
            build_python = ["py", "-" + PYTHON_VERSION[0]]
        else:
            build_python = ["python" + PYTHON_VERSION[0]]
        version_proc = subprocess.run(build_python + ["--version"], stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, universal_newlines=True)
        _, version = version_proc.stdout.split()  # e.g. "Python 3.7.1"
        return version


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


class RunGradle(object):
    @kwonly_defaults
    def __init__(self, test, run=True, key=None, *layers, **kwargs):
        self.test = test
        module, cls, func = re.search(r"^(\w+)\.(\w+)\.test_(\w+)$", test.id()).groups()
        self.run_dir = join(repo_root, "product/gradle-plugin/build/test/integration",
                            agp_version, cls, func)
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
            # We use dir_utils.copy_tree because shutil.copytree can't merge into a destination
            # that already exists.
            dir_util._path_created.clear()  # https://bugs.python.org/issue10948
            dir_util.copy_tree(join(integration_dir, "data", layer), self.project_dir,
                               preserve_times=False)  # https://github.com/gradle/gradle/issues/2301
            if layer == "base":
                self.apply_layers("base-" + agp_version)

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
    def rerun(self, succeed=True, variants=["debug"], *, env={}, **kwargs):
        status, self.stdout, self.stderr = self.run_gradle(variants, env)
        if status == 0:
            if succeed is False:  # (succeed is None) means we don't care
                self.dump_run("run unexpectedly succeeded")

            for variant in variants:
                outputs_apk_dir = join(self.project_dir, "app/build/outputs/apk")
                apk_zip = ZipFile(join(outputs_apk_dir,
                                       variant.replace("-", "/"),
                                       "app-{}.apk".format(variant)))
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
                    # Some tests check the cause type and message: search for
                    # `assertRaisesRegex(AssertionError`.
                    self.dump_run(f"check_apk failed: {type(e).__name__}: {e}")

            # Run a second time to check all tasks are considered up to date.
            first_msg = "\n=== FIRST RUN STDOUT ===\n" + self.stdout
            status, second_stdout, second_stderr = self.run_gradle(variants, env)
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

    def run_gradle(self, variants, env):
        merged_env = os.environ.copy()
        merged_env["chaquopy_root"] = repo_root
        merged_env["integration_dir"] = integration_dir
        merged_env.update(env)

        gradlew = join(self.project_dir,
                       "gradlew.bat" if sys.platform.startswith("win") else "gradlew")

        # `--info` explains why tasks were not considered up to date.
        # `--console plain` prevents "String index out of range: -1" error on Windows.
        gradlew_flags = ["--stacktrace", "--info", "--console", "plain"]
        if env:
            # Even if the Gradle client passes some environment variables to the daemon, that
            # won't work for TZ, because the JVM will only read it once.
            gradlew_flags.append("--no-daemon")

        process = subprocess.run([gradlew, "-p", self.project_dir] + gradlew_flags +
                                 [task_name("assemble", v) for v in variants],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 universal_newlines=True, env=merged_env, timeout=300)
        return process.returncode, process.stdout, process.stderr

    # TODO: refactor this into a set of independent methods, all using the same API as pre_check and
    # post_check.
    @kwonly_defaults
    def check_apk(self, apk_zip, apk_dir, abis=["x86"], classes=[], app=[],
                  requirements=[], reqs_versions=None, extract_packages=[], licensed_id=None,
                  **kwargs):
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
        self.test.checkZip(join(asset_dir, "app.zip"), app)

        # Python requirements
        for suffix in reqs_suffixes:
            self.test.checkZip(join(asset_dir, "requirements-{}.zip".format(suffix)),
                               (requirements[suffix] if isinstance(requirements, dict)
                                else requirements if suffix == "common"
                                else []),
                               reqs_versions if (suffix == "common") else None)

        # Python bootstrap
        bootstrap_native_dir = join(asset_dir, "bootstrap-native")
        self.test.assertEqual(sorted(abis), sorted(os.listdir(bootstrap_native_dir)))
        for abi in abis:
            self.test.assertEqual(["_ctypes.so", "java", "select.so"],
                                  sorted(os.listdir(join(bootstrap_native_dir, abi))))
            self.test.assertEqual(["__init__.py", "chaquopy.so"],
                                  sorted(os.listdir(join(bootstrap_native_dir, abi, "java"))))

        # Python stdlib
        stdlib_native_dir = join(asset_dir, "stdlib-native")
        self.test.assertCountEqual([abi + ".zip" for abi in abis],
                                   os.listdir(stdlib_native_dir))
        for abi in abis:
            stdlib_native_zip = ZipFile(join(stdlib_native_dir, abi + ".zip"))
            self.test.assertCountEqual(
                ["_hashlib.so", "_multiprocessing.so", "_socket.so", "_sqlite3.so",
                 "_ssl.so", "pyexpat.so", "unicodedata.so"],
                stdlib_native_zip.namelist())

        # libs
        self.test.assertCountEqual(abis, os.listdir(join(apk_dir, "lib")))
        for abi in abis:
            self.test.assertCountEqual(
                ["libchaquopy_java.so", "libcrypto_chaquopy.so", "libcrystax.so",
                 f"libpython{PYTHON_VERSION_SHORT}m.so", "libssl_chaquopy.so",
                 "libsqlite3.so"],
                os.listdir(join(apk_dir, "lib", abi)))

        # Chaquopy runtime library
        actual_classes = dex_classes(join(apk_dir, "classes.dex"))
        self.test.assertIn("com.chaquo.python.Python", actual_classes)

        # App Java classes
        self.test.assertEqual(sorted(("chaquopy_test." + c) for c in classes),
                              sorted(c for c in actual_classes if c.startswith("chaquopy_test")))

        # build.json
        DEFAULT_EXTRACT_PACKAGES = [  # See PythonPlugin.groovy
            "certifi", "cv2.data", "face_recognition_models", "ipykernel", "jedi.evaluate",
            "matplotlib", "nbformat", "notebook", "obspy", "parso", "pytz", "skimage.data",
            "skimage.io", "sklearn.datasets", "spacy.data", "theano"
        ]
        with open(join(asset_dir, "build.json")) as build_json_file:
            build_json = json.load(build_json_file)
        self.test.assertEqual(["assets", "extractPackages"], sorted(build_json))
        if extract_packages is not None:
            self.test.assertEqual(sorted(extract_packages + DEFAULT_EXTRACT_PACKAGES),
                                  sorted(build_json["extractPackages"]))
        asset_list = []
        for dirpath, dirnames, filenames in os.walk(asset_dir):
            asset_list += [relpath(join(dirpath, f), asset_dir).replace("\\", "/")
                           for f in filenames]
        self.test.assertEqual(
            {filename: file_sha1(join(asset_dir, filename))
             for filename in asset_list if filename != "build.json"},
            build_json["assets"])

        # Licensing
        ticket_filename = join(asset_dir, "ticket.txt")
        if licensed_id:
            license_dir = join(repo_root, "server/license")
            if license_dir not in sys.path:
                sys.path.append(license_dir)
            from check_ticket import check_ticket

            with open(join(repo_root, "server/license/public.pem")) as pub_key_file:
                import rsa
                pub_key = rsa.PublicKey.load_pkcs1(pub_key_file.read(), "PEM")
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


def file_sha1(filename):
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


# On Windows, rmtree often gets blocked by the virus scanner. See comment in our copy of
# pip/_internal/utils/misc.py.
def rmtree(path):
    if os.name == "nt":  # https://bugs.python.org/issue18199
        path = "\\\\?\\" + path.replace("/", "\\")
    shutil.rmtree(path, onerror=rmtree_errorhandler)

@retry(wait_fixed=50, stop_max_delay=3000)
def rmtree_errorhandler(func, path, exc_info):
    func(path)  # Use the original function to repeat the operation.
