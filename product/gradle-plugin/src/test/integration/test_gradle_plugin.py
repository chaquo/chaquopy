# This file requires the packages listed in requirements.txt.

from contextlib import contextmanager
from distutils import dir_util
import distutils.util
import hashlib
import json
import os
from os.path import abspath, basename, dirname, exists, join, relpath
import re
import shutil
from subprocess import run
import sys
from unittest import skip, skipIf, skipUnless, TestCase
from zipfile import ZipFile, ZIP_STORED

import appdirs
import javaproperties
from retrying import retry


integration_dir = abspath(dirname(__file__))
data_dir = join(integration_dir, "data")
repo_root = abspath(join(integration_dir, "../../../../.."))

# The following properties file should be created manually. It's also used in
# runtime/build.gradle.
with open(join(repo_root, "product/local.properties")) as props_file:
    sdk_dir = javaproperties.load(props_file)["sdk.dir"]

for line in open(join(repo_root, "product/buildSrc/src/main/java/com/chaquo/python/Common.java")):
    match = re.search(r'PYTHON_VERSION = "(.+)";', line)
    if match:
        PYTHON_VERSION = match[1]
        PYTHON_VERSION_SHORT = PYTHON_VERSION.rpartition(".")[0]
        break
else:
    raise Exception("Failed to find runtime Python version")


def run_build_python(args, **kwargs):
    for k, v in dict(check=True, capture_output=True, text=True).items():
        kwargs.setdefault(k, v)
    if os.name == "nt":
        build_python = ["py", "-" + PYTHON_VERSION_SHORT]
    else:
        build_python = ["python" + PYTHON_VERSION_SHORT]
    return run(build_python + args, **kwargs)

BUILD_PYTHON_VERSION = (run_build_python(["--version"]).stdout  # e.g. "Python 3.7.1"
                        .split()[1])
BUILD_PYTHON_VERSION_SHORT = BUILD_PYTHON_VERSION.rpartition(".")[0]
OLD_BUILD_PYTHON_VERSION = "3.4"
MIN_BUILD_PYTHON_VERSION = "3.5"
MAX_BUILD_PYTHON_VERSION = "3.9"
EGG_INFO_SUFFIX = "py" + BUILD_PYTHON_VERSION_SHORT + ".egg-info"
EGG_INFO_FILES = ["dependency_links.txt", "PKG-INFO", "SOURCES.txt", "top_level.txt"]


# Android Gradle Plugin version (passed from Gradle task).
agp_version = os.environ["AGP_VERSION"]
agp_version_info = tuple(map(int, agp_version.split(".")))

# This pattern causes Android Studio to show the line as a warning in tree view. However, the
# "Warning: " prefix will be removed, so the rest of the message should start with a capital
# letter.
WARNING = "^Warning: "


class GradleTestCase(TestCase):
    maxDiff = None

    def RunGradle(self, *args, **kwargs):
        return RunGradle(self, *args, **kwargs)

    @contextmanager
    def setLongMessage(self, value):
        old_value = self.longMessage
        self.longMessage = value
        yield
        self.longMessage = old_value

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

    def update_classes(self, dst, src):
        for package, src_names in src.items():
            dst_names = dst.setdefault(package, [])
            for name in src_names:
                if name not in dst_names:
                    dst_names.append(name)

    def check_classes(self, expected, actual):
        self.assertCountEqual(expected.keys(), actual.keys())
        for package, names in expected.items():
            with self.subTest(package=package):
                self.assertCountEqual(names, actual[package])

    # Asserts that the ZIP contains exactly the given files (do not include directories). Each
    # element of `files` must be either a filename, or a (filename, dict) tuple. The dict items
    # must either be attributes of ZipInfo, or a "content" string which will be compared with
    # the UTF-8 decoded file.
    #
    # The content of .dist_info directories is ignored unless `include_dist_info` is true.
    # However, the *names* of .dist_info directories can be tested by passing `dist_versions`
    # as a list of (name, version) tuples.
    def checkZip(self, zip_filename, files, *, pyc=False, include_dist_info=False,
                 dist_versions=None):
        with ZipFile(zip_filename) as zip_file:
            actual_files = []
            actual_dist_versions = set()
            for info in zip_file.infolist():
                with self.subTest(filename=info.filename):
                    self.assertEqual((1980, 2, 1, 0, 0, 0), info.date_time)
                    di_match = re.match(r"(.+)-(.+)\.(dist|egg)-info$",
                                        info.filename.split("/")[0])
                    if di_match:
                        actual_dist_versions.add(di_match.groups()[:2])
                        if not include_dist_info:
                            continue
                    if not info.filename.endswith("/"):
                        actual_files.append(info.filename)

            expected_files = []
            for f in files:
                with self.subTest(f=f):
                    filename, attrs = f if isinstance(f, tuple) else (f, {})
                    if pyc and filename.endswith(".py"):
                        filename += "c"
                    expected_files.append(filename)
                    zip_info = zip_file.getinfo(filename)

                    # Build machine paths should not be stored in the .pyc files.
                    if filename.endswith(".pyc"):
                        with self.setLongMessage(False):
                            self.assertNotIn(
                                repo_root.encode("UTF-8"), zip_file.read(zip_info),
                                msg=f"{repo_root!r} unexpectedly found in {filename}")

                    content_expected = attrs.pop("content", None)
                    if content_expected is not None:
                        content_actual = zip_file.read(zip_info).decode("UTF-8").strip()
                        self.assertEqual(content_expected, content_actual)
                    for key, value in attrs.items():
                        self.assertEqual(value, getattr(zip_info, key))

        self.assertCountEqual(expected_files, actual_files)
        if dist_versions is not None:
            self.assertCountEqual(dist_versions, list(actual_dist_versions))

    def pre_check(self, run, apk_dir, kwargs):
        pass

    def post_check(self, run, apk_dir, kwargs):
        pass


class Basic(GradleTestCase):
    def test_base(self):
        self.RunGradle("base")

    # The new Gradle plugins syntax is generated by the Android Studio wizard in version 4.1
    # and later, but is supported at least as far back as 3.4.
    def test_plugins(self):
        self.RunGradle("base", "Basic/plugins")

    def test_kwargs_wrapper(self):
        with self.assertRaisesRegex(AssertionError, "{'unused'} is not false"):
            self.RunGradle("base", unused=None)

    def test_variant(self):
        self.RunGradle("base", "Basic/variant", variants=["red-debug", "blue-debug"])


# Test that new versions of build-packages.zip are correctly extracted and used.
class ChaquopyPlugin(GradleTestCase):
    # Since this version, the extracted copy of build-packages.zip has been renamed to bp.zip.
    # We distinguish the old version by it not supporting arm64-v8a.
    def test_upgrade_3_0_0(self):
        run = self.RunGradle("base", "ChaquopyPlugin/upgrade_3_0_0", succeed=False)
        self.assertInLong("Chaquopy does not support the ABI 'arm64-v8a'", run.stderr)
        run.apply_layers("base", "ChaquopyPlugin/upgrade_current")
        run.rerun(abis=["arm64-v8a"])

    # Since this version, there has been no change in the build-packages.zip filename. We
    # distinguish the old version by it not supporting arm64-v8a.
    def test_upgrade_4_0_0(self):
        run = self.RunGradle("base", "ChaquopyPlugin/upgrade_4_0_0", succeed=False)
        self.assertInLong("Chaquopy does not support the ABI 'arm64-v8a'", run.stderr)
        run.apply_layers("base", "ChaquopyPlugin/upgrade_current")
        run.rerun(abis=["arm64-v8a"])


class AndroidPlugin(GradleTestCase):
    ADVICE = ("please edit the version of com.android.tools.build:gradle in your top-level "
              "build.gradle file. See https://chaquo.com/chaquopy/doc/current/versions.html.")

    def test_misordered(self):
        run = self.RunGradle("base", "AndroidPlugin/misordered", succeed=False)
        self.assertInLong(
            "project.android not set. Did you apply plugin com.android.application or "
            "com.android.library before com.chaquo.python?", run.stderr)

    def test_old(self):
        run = self.RunGradle("base", "AndroidPlugin/old", succeed=False)
        self.assertInLong("This version of Chaquopy requires Android Gradle plugin version "
                          "3.4.0 or later: " + self.ADVICE, run.stderr)

    def test_untested(self):  # Also tests making a change
        run = self.RunGradle("base")
        self.assertNotInLong("not been tested with Android Gradle plugin", run.stdout)

        run.apply_layers("AndroidPlugin/untested")
        try:
            run.rerun()
        except Exception:
            pass  # We don't care whether it succeeds.
        self.assertInLong(WARNING + "This version of Chaquopy has not been tested with Android "
                          "Gradle plugin versions beyond 4.1.2. If you experience "
                          "problems, " + self.ADVICE, run.stdout, re=True)


class Aar(GradleTestCase):
    def test_single_lib(self):
        self.RunGradle(
            "base", "Aar/single_lib",
            abis=["armeabi-v7a", "x86"],
            requirements={"common": ["apple/__init__.py"],
                          "armeabi-v7a": ["multi_abi_1_armeabi_v7a.pyd",
                                          ("multi_abi_1_pure/__init__.py",
                                           {"content": "# Clashing module (armeabi-v7a copy)"})],
                          "x86": ["multi_abi_1_x86.pyd",
                                  ("multi_abi_1_pure/__init__.py",
                                   {"content": "# Clashing module (x86 copy)"})]},
            app=[("one.py", {"content": "one"})],
            pyc=["stdlib"], aar="lib1")

    MULTI_MESSAGE = "More than one file was found with OS independent path 'lib/x86/"

    def test_multi_lib(self):
        run = self.RunGradle("base", "Aar/multi_lib", succeed=False)
        self.assertInLong(self.MULTI_MESSAGE, run.stderr)

    def test_lib_and_app(self):
        run = self.RunGradle("base", "Aar/lib_and_app")
        if agp_version_info >= (4, 0):
            self.assertInLong(self.MULTI_MESSAGE + r".* Future versions of the Android Gradle "
                              "Plugin will throw an error in this case.", run.stdout, re=True)

    def test_minify(self):
        self.RunGradle("base", "Aar/minify", aar="lib1")

    # AAR equivalent of RunGradle.check_apk.
    def post_check(self, run, apk_dir, kwargs):
        aar = kwargs.get("aar")
        if not aar:
            return

        aar_file, aar_dir = run.get_output(aar, basename(apk_dir), "aar")
        run.check_assets(aar_dir, kwargs)
        run.check_lib(f"{aar_dir}/jni", kwargs)

        # If minifyEnabled is set, the classes are all merged into classes.jar. Otherwise,
        # they'll be in libs/.
        aar_classes = {}
        for dirpath, dirnames, filenames in os.walk(aar_dir):
            for name in filenames:
                if name.endswith(".jar"):
                    with ZipFile(f"{dirpath}/{name}") as jar_file:
                        self.update_classes(aar_classes, jar_classes(jar_file))
        self.check_classes(chaquopy_classes(), aar_classes)


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


class JavaLib(GradleTestCase):

    # The Chaquopy plugin can't be used directly within a dynamic feature module, but if it's
    # used in the base module, then the Java API should be available to the feature module.
    def test_dynamic_feature(self):
        self.RunGradle("base", "JavaLib/dynamic_feature")

    # See comment in dex_classes. At some point in 2018, I saw the Chaquopy classes sometimes
    # ending up in classes2.dex when minSdkVersion was 21 or higher. I can't reproduce that now
    # with any supported Android Gradle plugin version, but include a test in case it changes
    # again in the future.
    def test_multidex(self):
        run = self.RunGradle("base")
        classes = f"{run.run_dir}/apk/debug/classes.dex"
        classes2 = f"{run.run_dir}/apk/debug/classes2.dex"
        self.assertTrue(exists(classes))
        self.assertFalse(exists(classes2))

        run.apply_layers("JavaLib/multidex")
        run.rerun()
        self.assertTrue(exists(classes))
        self.assertTrue(exists(classes2))

    # See also Aar.test_minify.
    def test_minify(self):
        self.RunGradle("base", "JavaLib/minify")

    def test_minify_variant(self):
        self.RunGradle("base", "JavaLib/minify_variant",
                       variants={"blue-debug": dict(classes={"com.example": ["Blue"]}),
                                 "red-debug":  dict(classes={"com.example": ["Red"]})})


class PythonVersion(GradleTestCase):
    def test_warning(self):
        message = (WARNING + "Python 'version' setting is no longer required and should be "
                   "removed from build.gradle.")
        run = self.RunGradle("base")
        self.assertNotInLong(message, run.stdout, re=True)
        run.apply_layers("PythonVersion/warning")
        run.rerun()
        self.assertInLong(message, run.stdout, re=True)

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
    def post_check(run, apk_dir, kwargs):
        for asset_path, expected_hash in hashes.items():
            test.assertEqual(expected_hash, file_sha1(f"{apk_dir}/assets/chaquopy/{asset_path}"))
    return post_check


class PythonSrc(GradleTestCase):
    def test_change(self):
        # Missing (as opposed to empty) src/main/python directory is already tested by Basic.
        #
        # Git can't track a directory hierarchy containing no files, and in this case even a
        # .gitignore file would invalidate the point of the test.
        empty_src = join(data_dir, "PythonSrc/empty/app/src/main/python")
        if not os.path.isdir(empty_src):
            os.makedirs(empty_src)
        run = self.RunGradle("base", "PythonSrc/empty")

        run.apply_layers("PythonSrc/1")                                 # Add
        run.rerun(app=[("one.py", {"content": "one"}), "package/submodule.py"], pyc=["stdlib"])
        run.apply_layers("PythonSrc/2")                                 # Modify
        run.rerun(app=[("one.py", {"content": "one modified"}), "package/submodule.py"],
                  pyc=["stdlib"])
        os.remove(join(run.project_dir, "app/src/main/python/one.py"))  # Remove
        run.rerun(app=["package/submodule.py"], pyc=["stdlib"])

    @skipIf(os.name == "posix", "For systems which don't support TZ variable")
    def test_reproducible_basic(self):
        self.post_check = make_asset_check(self, {
            "app.imy": "71ef4b2676498a2a2bb2c16d72d58ca2c4715936"})
        self.RunGradle("base", "PythonSrc/1", app=["one.py", "package/submodule.py"],
                       pyc=["stdlib"])

    @skipUnless(os.name == "posix", "For systems which support TZ variable")
    def test_reproducible_timezone(self):
        self.post_check = make_asset_check(self, {
            "app.imy": "71ef4b2676498a2a2bb2c16d72d58ca2c4715936"})

        app = ["one.py", "package/submodule.py"]
        for tz in ["UTC+0", "PST+8", "CET-1"]:  # + and - are reversed compared to normal usage.
            with self.subTest(tz=tz):
                self.RunGradle("base", "PythonSrc/1", app=app, env={"TZ": tz}, pyc=["stdlib"])

    def test_filter(self):
        run = self.RunGradle("base", "PythonSrc/filter_1", app=["one.py"])
        run.apply_layers("PythonSrc/filter_2")
        run.rerun(app=["two.py"])

    def test_variant(self):
        self.RunGradle(
            "base", "PythonSrc/variant",
            variants={"red-debug": dict(app=["common.py", ("color.py", {"content": "red"})]),
                      "blue-debug": dict(app=["common.py", ("color.py", {"content": "blue"})])},
            pyc=["stdlib"])

    def test_conflict(self):
        variants = {"red-debug": dict(app=["common.py", ("color.py", {"content": "red"})]),
                    "blue-debug": dict(app=["common.py", ("color.py", {"content": "blue"})])}
        run = self.RunGradle("base", "PythonSrc/conflict", variants=variants, succeed=False)
        self.assertInLong('(?s)mergeBlueDebugPythonSources.*Encountered duplicate path "common.py"',
                          run.stderr, re=True)
        run.apply_layers("PythonSrc/conflict_exclude")
        run.rerun(variants=variants, pyc=["stdlib"])
        run.apply_layers("PythonSrc/conflict_include")
        run.rerun(variants=variants, pyc=["stdlib"])

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
        if agp_version_info < (4, 1):
            self.assertInLong("Could not find method python()", run.stderr)
        else:
            # This is a much worse error message because it no longer indicates the line with
            # the unknown name, but it doesn't look as if there's anything we can do about it.
            self.assertInLong(r"No signature of method: build_\w+\.android\(\) is applicable",
                              run.stderr, re=True)

    @skip("TODO #5341 setRoot not implemented")
    def test_set_root(self):
        self.RunGradle("base", "PythonSrc/set_root", app=["two.py"],
                       classes={"chaquopy_test": ["Two"]}, pyc=["stdlib"])


class ExtractPackages(GradleTestCase):
    def test_warning(self):
        message = (WARNING + "Python 'extractPackages' setting is no longer required and should "
                   "be removed from build.gradle.")
        run = self.RunGradle("base")
        self.assertNotInLong(message, run.stdout, re=True)
        run.apply_layers("ExtractPackages/warning")
        run.rerun()
        self.assertInLong(message, run.stdout, re=True)


class Pyc(GradleTestCase):
    FAILED = "Failed to compile to .pyc format: "
    INCOMPATIBLE = r"buildPython version 3.5.\d+ is incompatible. "
    SEE = "See https://chaquo.com/chaquopy/doc/current/android.html#android-bytecode."

    def test_change(self):
        kwargs = dict(app=["hello.py"], requirements=["six.py"])
        run = self.RunGradle("base", "Pyc/change_1", **kwargs)
        run.apply_layers("Pyc/change_2")
        run.rerun(pyc=[], **kwargs)

    def test_variant(self):
        self.RunGradle("base", "Pyc/variant", app=["hello.py"], requirements=["six.py"],
                       variants={"red-debug": dict(pyc=["src", "pip", "stdlib"]),
                                 "blue-debug": dict(pyc=[])})

    def test_variant_merge(self):
        self.RunGradle("base", "Pyc/variant_merge", app=["hello.py"], requirements=["six.py"],
                       variants={"red-debug": dict(pyc=[]),
                                 "blue-debug": dict(pyc=["src", "pip", "stdlib"])})

    def test_syntax_error(self):
        self.RunGradle("base", "Pyc/syntax_error", app=["bad.py", "good.pyc"], pyc=["stdlib"])

    def test_build_python_warning(self):
        run = self.RunGradle("base", "Pyc/build_python_warning", pyc=["stdlib"])
        self.assertInLong(WARNING + self.FAILED + BuildPython.PROBLEM.format("pythoninvalid") +
                          self.SEE, run.stdout, re=True)

        run.apply_layers("Pyc/build_python_warning_suppress")
        run.rerun(pyc=["stdlib"])
        self.assertNotInLong(self.FAILED, run.stdout)

    def test_build_python_error(self):
        run = self.RunGradle("base", "Pyc/build_python_error", succeed=False)
        self.assertInLong(BuildPython.INVALID.format("pythoninvalid"), run.stderr, re=True)

    def test_magic_warning(self):
        run = self.RunGradle("base", "Pyc/magic_warning", requirements=["six.py"], pyc=["stdlib"])
        self.assertInLong(WARNING + self.FAILED + self.INCOMPATIBLE + self.SEE,
                          run.stdout, re=True)

    def test_magic_error(self):
        run = self.RunGradle("base", "Pyc/magic_error", succeed=False)
        self.assertInLong(self.FAILED + self.INCOMPATIBLE + self.SEE, run.stdout, re=True)
        self.assertInLong(BuildPython.FAILED, run.stderr, re=True)


class BuildPython(GradleTestCase):
    # Some of these messages are also used in other test classes.
    SEE = "See https://chaquo.com/chaquopy/doc/current/android.html#buildpython."
    ADVICE = "set buildPython to your Python executable path. " + SEE
    PROBLEM = "A problem occurred starting process 'command '{}''. "
    INVALID = PROBLEM + "Please " + ADVICE
    INSTALL = "Please either install it, or " + ADVICE
    FAILED = (r"Process 'command '.+'' finished with non-zero exit value 1\n\n"
              r"To view full details in Android Studio:\n"
              r"\* In version 3.6 and newer, click the 'Build: failed' caption to the left of "
              r"this message.\n"
              r"\* In version 3.5 and older, click the 'Toggle view' button to the left of "
              r"this message.\n"
              r"\* Then scroll up to see the full output.")

    @classmethod
    def old_version_error(cls, version):
        return (fr"buildPython must be version {MIN_BUILD_PYTHON_VERSION} or later: "
                fr"this is version {version}\.\d+\. " + cls.SEE)

    def test_args(self):  # Also tests making a change.
        run = self.RunGradle("base", "BuildPython/args_1", succeed=False)
        self.assertInLong("echo_args1", run.stdout)
        run.apply_layers("BuildPython/args_2")
        run.rerun(succeed=False)
        self.assertInLong("echo_args2", run.stdout)

    def test_space(self):
        run = self.RunGradle("base", "BuildPython/space", succeed=False)
        self.assertInLong("Hello Chaquopy", run.stdout)

    def test_missing(self):
        run = self.RunGradle("base", "BuildPython/missing", add_path=["bin"], succeed=False)
        self.assertInLong("Couldn't find Python. " + self.INSTALL, run.stderr)

    def test_missing_minor(self):
        run = self.RunGradle("base", "BuildPython/missing_minor", add_path=["bin"],
                             succeed=False)
        self.assertNotInLong("Minor version was used", run.stdout)
        self.assertInLong("Major version was used", run.stdout)

    def test_missing_major(self):
        run = self.RunGradle("base", "BuildPython/missing_major", add_path=["bin"],
                             succeed=False)
        self.assertInLong("Minor version was used", run.stdout)
        self.assertNotInLong("Major version was used", run.stdout)

    @skipUnless(os.name == "nt", "Windows-specific")
    def test_py_not_found(self):
        run = self.RunGradle("base", "BuildPython/py_not_found", succeed=False)
        self.assertInLong("[py, -2.8]: couldn't find the requested version of Python. " +
                          self.INSTALL, run.stderr)

    # Test a buildPython which returns success without doing anything (#5631).
    def test_silent_failure(self):
        run = self.RunGradle("base", "BuildPython/silent_failure", succeed=False)
        self.assertInLong("common was not created: please check your buildPython setting",
                          run.stderr)

    def test_variant(self):
        run = self.RunGradle("base", "BuildPython/variant", variants=["red-debug"],
                             succeed=False)
        self.assertInLong(self.INVALID.format("python-red"), run.stderr, re=True)
        run.rerun(variants=["blue-debug"], succeed=False)
        self.assertInLong(self.INVALID.format("python-blue"), run.stderr, re=True)

    def test_variant_merge(self):
        run = self.RunGradle("base", "BuildPython/variant_merge", variants=["red-debug"],
                             succeed=False)
        self.assertInLong(self.INVALID.format("python-red"), run.stderr, re=True)
        run.rerun(variants=["blue-debug"], succeed=False)
        self.assertInLong(self.INVALID.format("python-blue"), run.stderr, re=True)


class PythonReqs(GradleTestCase):
    def test_change(self):
        # No reqs.
        run = self.RunGradle("base")

        # Add one req.
        run.apply_layers("PythonReqs/1a")
        run.rerun(requirements=["apple/__init__.py"],
                  dist_versions=[("apple", "0.0.1")])

        # Replace with a req which has a transitive dependency.
        run.apply_layers("PythonReqs/1")
        run.rerun(requirements=["alpha/__init__.py", "alpha_dep/__init__.py"],
                  dist_versions=[("alpha", "0.0.1"), ("alpha_dep", "0.0.1")])

        # Add another req.
        run.apply_layers("PythonReqs/2")
        run.rerun(
            requirements=["alpha/__init__.py", "alpha_dep/__init__.py", "bravo/__init__.py"],
            dist_versions=[("alpha", "0.0.1"), ("alpha_dep", "0.0.1"), ("bravo", "0.0.1")])

        # Remove all.
        run.apply_layers("base")
        run.rerun()

    # When pip fails, make sure we tell the user how to see the full output.
    def test_fail(self):
        run = self.RunGradle("base", "PythonReqs/fail", succeed=False)
        self.assertInLong("No matching distribution found for chaquopy-nonexistent", run.stderr)
        self.assertInLong(BuildPython.FAILED, run.stderr, re=True)

    def test_buildpython(self):
        # Use a fresh RunGradle instance for each test in order to clear the pip cache.
        layers = ["base", "PythonReqs/buildpython"]

        for version in [MIN_BUILD_PYTHON_VERSION, MAX_BUILD_PYTHON_VERSION]:
            with self.subTest(version=version):
                self.RunGradle(*layers, env={"buildpython_version": version},
                               requirements=["apple/__init__.py",
                                             "no_binary_sdist/__init__.py"],
                               pyc=["stdlib"])

        # Make sure we've kept valid Python 2 syntax so we can produce a useful error message.
        for version in ["2.7", OLD_BUILD_PYTHON_VERSION]:
            with self.subTest(version=version):
                run = self.RunGradle(*layers, env={"buildpython_version": version},
                                     succeed=False)
                self.assertInLong(BuildPython.old_version_error(version), run.stderr, re=True)

    def test_download_wheel(self):
        CHAQUO_URL = r"https://.+/murmurhash-0.28.0-5-cp38-cp38-android_16_x86.whl"
        PYPI_URL = r"https://.+/six-1.14.0-py2.py3-none-any.whl"
        common_reqs = (["murmurhash/" + name for name in
                        ["__init__.pxd", "__init__.py", "about.py", "mrmr.pxd", "mrmr.pyx",
                         "include/murmurhash/MurmurHash2.h", "include/murmurhash/MurmurHash3.h",
                         "tests/__init__.py", "tests/test_import.py"]] +
                       ["chaquopy_libcxx-7000.dist-info/" + name for name in
                        ["INSTALLER", "LICENSE.TXT", "METADATA"]] +
                       ["murmurhash-0.28.0.dist-info/" + name for name in
                        ["INSTALLER", "LICENSE", "METADATA", "top_level.txt"]])
        abi_reqs = ["chaquopy/lib/libc++_shared.so", "murmurhash/mrmr.so"]
        kwargs = dict(
            abis=["armeabi-v7a", "x86"],
            requirements={"common": common_reqs, "armeabi-v7a": abi_reqs, "x86": abi_reqs},
            include_dist_info=True)
        run = self.RunGradle("base", "PythonReqs/download_wheel_1", **kwargs)
        self.assertInLong("Downloading " + CHAQUO_URL, run.stdout, re=True)
        run.apply_layers("PythonReqs/download_wheel_2")
        common_reqs += (["six.py"] +
                        ["six-1.14.0.dist-info/" + name
                         for name in ["INSTALLER", "LICENSE", "METADATA", "top_level.txt"]])
        run.rerun(**kwargs)
        self.assertInLong("Using cached " + CHAQUO_URL, run.stdout, re=True)
        self.assertInLong("Downloading " + PYPI_URL, run.stdout, re=True)

    # Some packages with optional native components generate a wheel tagged with the build
    # platform even when the native components are omitted. This wheel must be renamed in order
    # for it to be used in the rerun.
    def test_download_sdist(self):
        URL = r"https://.+/PyYAML-3.12.tar.gz"
        BUILD = r"Successfully built PyYAML"
        reqs = ["yaml/" + name + ".py" for name in
                ["__init__", "composer", "constructor", "cyaml", "dumper", "emitter", "error",
                 "events", "loader", "nodes", "parser", "reader", "representer", "resolver",
                 "scanner", "serializer", "tokens"]]
        run = self.RunGradle("base", "PythonReqs/download_sdist_1", requirements=reqs)
        self.assertInLong("Downloading " + URL, run.stdout, re=True)
        self.assertInLong(BUILD, run.stdout, re=True)
        run.apply_layers("PythonReqs/download_sdist_2")
        run.rerun(requirements=reqs + ["six.py"])
        # pip prints lots of detail when it puts a wheel into the cache, but says absolutely
        # nothing when it takes one out.
        self.assertNotInLong(URL, run.stdout)
        self.assertNotInLong(BUILD, run.stdout)

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

    def test_cfg_wheel(self):
        self.RunGradle("base", "PythonReqs/cfg_wheel", requirements=["apple/__init__.py"])

    # We need to fall back on setup.py install to test this, because bdist_wheel doesn't use
    # --prefix or --home.
    def test_cfg_sdist(self):
        run = self.RunGradle("base", "PythonReqs/cfg_sdist",
                             requirements=["bdist_wheel_fail/__init__.py"])
        self.assertInLong("Failed to build bdist-wheel-fail", run.stdout)
        self.assertInLong(self.RUNNING_INSTALL, run.stdout)

    # By checking that this string is output in tests which fall back on setup.py install, we
    # can use the absence of the string in other tests to prove that no fallback occurred.
    RUNNING_INSTALL = "Running setup.py install"

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

                # If bdist_wheel fails with a "native code" message, we should not fall back on
                # setup.py install.
                self.assertNotInLong(self.RUNNING_INSTALL, run.stdout)

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

    # If bdist_wheel fails without a "native code" message, we should fall back on setup.py
    # install. For example, see acoustics==0.2.4 (#5630).
    def test_bdist_wheel_fail(self):
        run = self.RunGradle(
            "base", "PythonReqs/bdist_wheel_fail", include_dist_info=True,
            requirements=([f"bdist_wheel_fail-1.0-{EGG_INFO_SUFFIX}/{name}"
                           for name in EGG_INFO_FILES] +
                          ["bdist_wheel_fail/__init__.py"]))
        self.assertInLong("bdist_wheel throwing exception", run.stdout)
        self.assertInLong("Failed to build bdist-wheel-fail", run.stdout)
        self.assertInLong(self.RUNNING_INSTALL, run.stdout)

    # If bdist_wheel returns success but didn't generate a wheel, we should fall back on
    # setup.py install. For example, see kiteconnect==3.8.2 (#5630).
    def test_bdist_wheel_fail_silently(self):
        run = self.RunGradle(
            "base", "PythonReqs/bdist_wheel_fail_silently", include_dist_info=True,
            requirements=([f"bdist_wheel_fail_silently-1.0-{EGG_INFO_SUFFIX}/{name}"
                           for name in EGG_INFO_FILES] +
                          ["bdist_wheel_fail_silently/__init__.py"]))
        self.assertInLong("Failed to build bdist-wheel-fail-silently", run.stdout)
        self.assertInLong(self.RUNNING_INSTALL, run.stdout)

    # site-packages should not be visible to setup.py scripts.
    def test_sdist_site(self):
        # The default buildPython should be the same Python executable as is running this test
        # script, but make sure by checking for one of this script's requirements.
        PKG_NAME = "javaproperties"
        run_build_python(["-c", f"import {PKG_NAME}"])

        run = self.RunGradle("base", "PythonReqs/sdist_site",
                             env={"CHAQUOPY_PKG_NAME": PKG_NAME}, succeed=False)
        self.assertInLong(f"No module named '{PKG_NAME}'", run.stdout)

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
    #   1.3: compatible native wheel
    #   1.6: incompatible native wheel (should be ignored)
    #   1.8: pure wheels (with two build numbers)
    #   2.0: sdist
    def test_mixed_index(self):
        # With no version restriction, the compatible native wheel is preferred over the sdist
        # and the pure wheels, despite having a lower version.
        run = self.RunGradle("base", "PythonReqs/mixed_index_1",
                             requirements=[("native3_android_15_x86/__init__.py",
                                            {"content": "# Version 1.3"})],
                             pyc=["stdlib"])
        self.assertInLong("Using version 1.3 (newest version is 2.0, but Chaquopy prefers "
                          "native wheels", run.stdout)

        # With "!=1.3", the sdist is selected, but it will fail at the egg_info stage. (Failure
        # at later stages is covered by test_sdist_native.) Version 1.8 has two build numbers
        # available, but should only be listed once in the message.
        run.apply_layers("PythonReqs/mixed_index_2")
        run.rerun(succeed=False)
        self.assertInLong(r"Failed to install native3!=1.3 from "
                          r"file:.*dist/native3-2.0.tar.gz." + self.tracker_advice() +
                          self.wheel_advice(["1.3", "1.8"]) + r"$",
                          run.stderr, re=True)

        # With "!=1.3,!=2.0", the pure wheel with the higher build number is selected.
        run.apply_layers("PythonReqs/mixed_index_3")
        run.rerun(requirements=[("native3_pure_1/__init__.py",
                                 {"content": "# Version 1.8"})],
                  pyc=["stdlib"])

    def test_no_binary_fail(self):
        # This is the same as mixed_index_2, except the wheels are excluded from consideration
        # using --no-binary, so the wheel advice won't appear.
        run = self.RunGradle("base", "PythonReqs/no_binary_fail", succeed=False)
        self.assertInLong(r"Failed to install native3 from file:.*dist/native3-2.0.tar.gz." +
                          self.tracker_advice() + r"$",
                          run.stderr, re=True)
        self.assertNotInLong(self.WHEEL_ADVICE, run.stderr)

    def test_no_binary_succeed(self):
        run = self.RunGradle("base", "PythonReqs/no_binary_succeed",
                             requirements=["no_binary_sdist/__init__.py"])
        self.assertInLong("Skipping bdist_wheel", run.stdout)
        self.assertInLong(self.RUNNING_INSTALL, run.stdout)

    def test_requires_python(self):
        self.assertNotEqual(BUILD_PYTHON_VERSION, PYTHON_VERSION)
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
            print_link("0.2", BUILD_PYTHON_VERSION)
            print("</body></html>", file=index_file)

        run.rerun(requirements=["pyver.py"], dist_versions=[("pyver", "0.1")])

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
            "requirements-common.imy": "844bc1e437bddd8ec9168fbc3858f70d17e0d0af",
            "requirements-armeabi-v7a.imy": "8ef282896a9a057d363dd7e294d52f89a80ae36a",
            "requirements-x86.imy": "4d0c2dfb5ac62016df8deceb9d827abd6a16cc48"})

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
                                  "pkg/submodule_x86.pyd"]},
            pyc=["stdlib"])

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
                                   {"content": "# Clashing module (x86 copy)"})]},
            pyc=["stdlib"])

    # ABIs should be installed in alphabetical order. (In the order specified is not possible
    # because the Android Gradle plugin keeps abiFilters in a HashSet.)
    def test_multi_abi_order(self):
        # armeabi-v7a will install a pure-Python wheel, so the requirement will not be
        # installed again for x86, even though an x86 wheel is available.
        run = self.RunGradle("base", "PythonReqs/multi_abi_order_1", abis=["armeabi-v7a", "x86"],
                             requirements=["multi_abi_order_pure/__init__.py"],
                             dist_versions=[("multi_abi_order", "0.1")])

        # armeabi-v7a will install a native wheel, so the requirement will be installed again
        # for x86, which will select the pure-Python wheel.
        run.apply_layers("PythonReqs/multi_abi_order_2")
        run.rerun(abis=["armeabi-v7a", "x86"],
                  requirements={"common": [],
                                "armeabi-v7a": ["multi_abi_order_armeabi_v7a.pyd"],
                                "x86": ["multi_abi_order_pure/__init__.py"]},
                  dist_versions=[("multi_abi_order", "0.2")])

    def test_namespace_packages(self):
        self.RunGradle("base", "PythonReqs/namespace_packages",
                       requirements=["pkg1/a.py", "pkg1/b.py",
                                     "pkg2/a.py", "pkg2/b.py",
                                     "pkg2/pkg21/a.py", "pkg2/pkg21/b.py",
                                     "pkg3/pkg31/a.py", "pkg3/pkg31/b.py"])

    # Files which aren't needed at runtime should be omitted from the APK.
    def test_chaquopy_dir(self):
        self.RunGradle("base", "PythonReqs/chaquopy_dir",
                       requirements=["chaquopy/chaquopy_file.txt",
                                     "chaquopy/bin/bin_file.txt",
                                     "chaquopy/lib/lib_file.txt",
                                     "chaquopy/lib/subdir/lib_subdir_file.txt"])

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
                                 ("pkg/id.py", {"content": "# x86"})]},
            pyc=["stdlib"])

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
                                 ("pkg/id.py", {"content": "# x86"})]},
            pyc=["stdlib"])

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
                          "aa_before.py", "zz_before.py", "aa_after.py", "zz_after.py"],
            pyc=["stdlib"])

        run.apply_layers("PythonReqs/duplicate_filenames_single_abi_np")
        run.rerun(requirements=["pkg/__init__.py", "pkg/native_only.py", "pkg/pure_only.py",
                                "native_x86.pyd",
                                ("pkg/dd.py", {"content": "# pure #############"}),
                                ("pkg/di.py", {"content": "# pure"}),
                                ("pkg/id.py", {"content": "# pure and armeabi-v7a"}),
                                ("pkg/ii.py", {"content": "# pure, armeabi-v7a and x86"}),
                                "aa_before.py", "zz_before.py", "aa_after.py", "zz_after.py"],
                  pyc=["stdlib"])

    @skipIf("linux" in sys.platform, "Non-Linux build platforms only")
    def test_marker_platform(self):
        self.RunGradle("base", "PythonReqs/marker_platform", requirements=["linux.py"])

    def test_marker_python_version(self):
        self.assertNotEqual(BUILD_PYTHON_VERSION, PYTHON_VERSION)
        run = self.RunGradle("base", "PythonReqs/marker_python_version", run=False)
        with open(f"{run.project_dir}/app/requirements.txt", "w") as reqs_file:
            def print_req(whl_version, python_version):
                print(f'pyver-{whl_version}-py2.py3-none-any.whl; '
                      f'python_full_version == "{python_version}"', file=reqs_file)

            # If the build Python version is used, or the environment markers are ignored
            # completely, then version 0.2 will be selected.
            print_req("0.1", PYTHON_VERSION)
            print_req("0.2", BUILD_PYTHON_VERSION)

        run.rerun(requirements=["pyver.py"], dist_versions=[("pyver", "0.1")])

    def tracker_advice(self):
        return ("\nFor assistance, please raise an issue at "
                "https://github.com/chaquo/chaquopy/issues.")

    WHEEL_ADVICE = ("Or try using one of the following versions, which are available as "
                    "pre-built wheels")

    def wheel_advice(self, versions):
        return re.escape(f"\n{self.WHEEL_ADVICE}: {versions!r}.")


class StaticProxy(GradleTestCase):
    reqs = ["chaquopy_test/__init__.py", "chaquopy_test/a.py", "chaquopy_test/b.py"]

    def test_buildpython(self):
        layers = ["base", "StaticProxy/buildpython"]

        for version in [MIN_BUILD_PYTHON_VERSION, MAX_BUILD_PYTHON_VERSION]:
            with self.subTest(version=version):
                self.RunGradle(*layers, env={"buildpython_version": version},
                               app=["chaquopy_test/__init__.py", "chaquopy_test/a.py"],
                               classes={"chaquopy_test.a": ["SrcA1"]},
                               pyc=["stdlib"])

        # Make sure we've kept valid Python 2 syntax so we can produce a useful error message.
        for version in ["2.7", OLD_BUILD_PYTHON_VERSION]:
            with self.subTest(version=version):
                run = self.RunGradle(*layers, env={"buildpython_version": version},
                                     succeed=False)
                self.assertInLong(BuildPython.old_version_error(version), run.stderr, re=True)

    def test_change(self):
        run = self.RunGradle("base", "StaticProxy/reqs", requirements=self.reqs,
                             classes={"chaquopy_test.a": ["ReqsA1"],
                                      "chaquopy_test.b": ["ReqsB1"]})
        app = ["chaquopy_test/__init__.py", "chaquopy_test/a.py"]
        run.apply_layers("StaticProxy/src_1")       # Src should take priority over reqs.
        run.rerun(requirements=self.reqs, app=app, classes={"chaquopy_test.a": ["SrcA1"],
                                                            "chaquopy_test.b": ["ReqsB1"]})
        run.apply_layers("StaticProxy/src_only")    # Change staticProxy setting
        run.rerun(app=app, requirements=self.reqs, classes={"chaquopy_test.a": ["SrcA1"]})
        run.apply_layers("StaticProxy/src_2")       # Change source code
        run.rerun(app=app, requirements=self.reqs, classes={"chaquopy_test.a": ["SrcA2"]})
        run.apply_layers("base")                    # Remove all
        run.rerun(app=app)

    def test_variant(self):
        self.RunGradle("base", "StaticProxy/variant",
                       requirements=self.reqs,
                       variants={"red-debug":  dict(classes={"chaquopy_test.a": ["ReqsA1"]}),
                                 "blue-debug": dict(classes={"chaquopy_test.b": ["ReqsB1"]})})

    def test_variant_merge(self):
        self.RunGradle("base", "StaticProxy/variant_merge",
                       requirements=self.reqs,
                       variants={"red-debug":  dict(classes={"chaquopy_test.a": ["ReqsA1"]}),
                                 "blue-debug": dict(classes={"chaquopy_test.a": ["ReqsA1"],
                                                             "chaquopy_test.b": ["ReqsB1"]})})


class RunGradle(object):
    def __init__(self, test, *layers, run=True, **kwargs):
        self.test = test
        module, cls, func = re.search(r"^(\w+)\.(\w+)\.test_(\w+)$", test.id()).groups()
        self.run_dir = join(repo_root, "product/gradle-plugin/build/test/integration",
                            agp_version, cls, func)
        if os.path.exists(self.run_dir):
            rmtree(self.run_dir)

        # Keep each test independent by clearing the pip cache. The appdirs module used in
        # pip._internal.locations is an old or modified version imported from
        # pip._internal.utils, which is why pip doesn't need to pass `appauthor`.
        cache_dir = appdirs.user_cache_dir("chaquopy/pip", appauthor=False)
        if exists(cache_dir):
            rmtree(cache_dir)

        self.project_dir = join(self.run_dir, "project")
        os.makedirs(self.project_dir)
        self.apply_layers(*layers)
        self.set_local_property("sdk.dir", sdk_dir)
        if run:
            self.rerun(**kwargs)

    def apply_layers(self, *layers):
        for layer in layers:
            # We use dir_utils.copy_tree because shutil.copytree can't merge into a destination
            # that already exists.
            dir_util._path_created.clear()  # https://bugs.python.org/issue10948
            dir_util.copy_tree(join(data_dir, layer), self.project_dir,
                               preserve_times=False)  # https://github.com/gradle/gradle/issues/2301
            if layer == "base":
                self.apply_layers("base-" + agp_version)

    def set_local_property(self, key, value):
        filename = join(self.project_dir, "local.properties")
        try:
            with open(filename) as props_file:
                props = javaproperties.load(props_file)
        except FileNotFoundError:
            props = {}

        if value is None:
            props.pop(key, None)
        else:
            props[key] = value
        with open(filename, "w") as props_file:
            javaproperties.dump(props, props_file)

    def rerun(self, *, succeed=True, variants=["debug"], env=None, add_path=None, **kwargs):
        if env is None:
            env = {}
        if add_path:
            add_path = [join(self.project_dir, path) for path in add_path]
            if os.name == "nt":
                # Gradle runs subprocesses using Java's ProcessBuilder, which in turn uses
                # CreateProcessW. This uses a search algorithm which has some differences from
                # the one used by the cmd shell:
                #   * The only extension it tries is .exe, so we can't use a .bat file here.
                #   * It searches the Windows directory (where the real py.exe is installed)
                #     before trying the PATH, so overriding PATH is no use here. Instead, we
                #     copy the files to the working directory, which has even higher priority.
                for path in add_path:
                    for entry in os.scandir(path):
                        if entry.is_file():
                            shutil.copy(entry.path, self.project_dir)
            else:
                env["PATH"] = os.pathsep.join(add_path + [os.environ["PATH"]])

        status, self.stdout, self.stderr = self.run_gradle(variants, env)
        if status == 0:
            if not succeed:
                self.dump_run("run unexpectedly succeeded")

            for variant in variants:
                merged_kwargs = kwargs.copy()
                merged_kwargs.setdefault("abis", ["x86"])
                if isinstance(variants, dict):
                    merged_kwargs.update(variants[variant])
                merged_kwargs = KwargsWrapper(merged_kwargs)
                try:
                    self.check_apk(variant, merged_kwargs)
                except Exception as e:
                    self.dump_run(f"check_apk failed: {type(e).__name__}: {e}")
                self.test.assertFalse(merged_kwargs.unused_kwargs)

            # Run a second time to check all tasks are considered up to date.
            first_stdout = self.stdout
            status, second_stdout, second_stderr = self.run_gradle(variants, env)
            if status != 0:
                self.stdout, self.stderr = second_stdout, second_stderr
                self.dump_run("Second run: exit status {}".format(status))

            num_tasks = 0
            for line in second_stdout.splitlines():
                if re.search(r"^> Task .*Python", line):
                    self.test.assertIn("UP-TO-DATE", line,
                                       msg=("=== FIRST RUN ===\n" + first_stdout +
                                            "=== SECOND RUN ===\n" + second_stdout))
                    num_tasks += 1
            self.test.assertGreater(num_tasks, 0, msg=second_stdout)

        else:
            if succeed:
                self.dump_run("exit status {}".format(status))

    def run_gradle(self, variants, env):
        merged_env = os.environ.copy()
        merged_env["chaquopy_root"] = repo_root
        merged_env["integration_dir"] = integration_dir
        merged_env.update(env)

        # `--info` explains why tasks were not considered up to date.
        # `--console plain` prevents "String index out of range: -1" error on Windows.
        gradlew_flags = ["--stacktrace", "--info", "--console", "plain"]
        if env:
            # The Gradle client passes its environment to the daemon, but that won't work for
            # TZ, because the JVM only reads it during startup.
            gradlew_flags.append("--no-daemon")

        process = run([join(self.project_dir,
                            "gradlew.bat" if (os.name == "nt") else "gradlew")] +
                      gradlew_flags + [task_name("assemble", v) for v in variants],
                      cwd=self.project_dir,  # See add_path above.
                      capture_output=True, text=True, env=merged_env, timeout=600)
        return process.returncode, process.stdout, process.stderr

    def check_apk(self, variant, kwargs):
        apk_zip, apk_dir = self.get_output("app", variant, "apk")
        self.test.pre_check(self, apk_dir, kwargs)

        # All AssetFinder ZIPs should be stored uncompressed (see comment in Common.assetZip).
        for info in apk_zip.infolist():
            if info.filename.endswith(".imy"):
                self.test.assertEqual(ZIP_STORED, info.compress_type, info.filename)

        self.check_assets(apk_dir, kwargs)
        self.check_lib(f"{apk_dir}/lib", kwargs)

        classes = kwargs.get("classes", {})
        self.test.update_classes(classes, chaquopy_classes())
        self.test.check_classes(classes, dex_classes(apk_dir))

        self.test.post_check(self, apk_dir, kwargs)

    def get_output(self, module, variant, ext):
        output_dir = join(self.project_dir, f"{module}/build/outputs/{ext}")
        if ext == "apk":
            output_dir = join(output_dir, variant.replace("-", "/"))
        zip_file = ZipFile(f"{output_dir}/{module}-{variant}.{ext}")

        zip_dir = join(self.run_dir, ext, variant)
        if exists(zip_dir):
            rmtree(zip_dir)
        zip_file.extractall(zip_dir)
        return zip_file, zip_dir

    def check_assets(self, apk_dir, kwargs):
        # Top-level assets
        asset_dir = join(apk_dir, "assets/chaquopy")
        abis = kwargs["abis"]
        abi_suffixes = ["common"] + abis
        self.test.assertCountEqual(
            ["app.imy", "bootstrap-native", "bootstrap.imy", "build.json", "cacert.pem",
             "ticket.txt"] + [f"{stem}-{suffix}.imy" for stem in ["requirements", "stdlib"]
                              for suffix in abi_suffixes],
            os.listdir(asset_dir))

        # Python source
        pyc = kwargs.get("pyc", ["src", "pip", "stdlib"])
        self.test.checkZip(f"{asset_dir}/app.imy", kwargs.get("app", []),
                           pyc=("src" in pyc))

        # Python requirements
        requirements = kwargs.get("requirements", [])
        for suffix in abi_suffixes:
            with self.test.subTest(suffix=suffix):
                self.test.checkZip(
                    f"{asset_dir}/requirements-{suffix}.imy",
                    (requirements[suffix] if isinstance(requirements, dict)
                     else requirements if suffix == "common"
                     else []),
                    pyc=("pip" in pyc),
                    include_dist_info=kwargs.get("include_dist_info", False),
                    dist_versions=(kwargs.get("dist_versions") if suffix == "common"
                                   else None))

        # Python bootstrap
        bootstrap_native_dir = join(asset_dir, "bootstrap-native")
        self.test.assertCountEqual(abis, os.listdir(bootstrap_native_dir))
        for abi in abis:
            self.test.assertCountEqual(
                ["java", "_csv.so", "_ctypes.so", "_datetime.so",  "_hashlib.so", "_json.so",
                 "_random.so", "_struct.so", "binascii.so", "math.so", "mmap.so", "zlib.so"],
                os.listdir(join(bootstrap_native_dir, abi)))
            self.test.assertCountEqual(
                ["__init__.py", "chaquopy.so", "chaquopy_android.so"],
                os.listdir(join(bootstrap_native_dir, abi, "java")))

        # Python stdlib
        stdlib_files = set(ZipFile(join(asset_dir, "stdlib-common.imy")).namelist())
        self.test.assertEqual("stdlib" in pyc, "argparse.pyc" in stdlib_files)
        self.test.assertNotEqual("stdlib" in pyc, "argparse.py" in stdlib_files)

        # Data files packaged with stdlib: see target/package_target.sh.
        for grammar_stem in ["Grammar", "PatternGrammar"]:
            self.test.assertIn("lib2to3/{}{}.final.0.pickle"
                               .format(grammar_stem, PYTHON_VERSION), stdlib_files)

        for abi in abis:
            stdlib_native_zip = ZipFile(join(asset_dir, f"stdlib-{abi}.imy"))
            self.test.assertCountEqual(
                ["_asyncio.so", "_bisect.so", "_blake2.so", "_bz2.so", "_codecs_cn.so",
                 "_codecs_hk.so", "_codecs_iso2022.so", "_codecs_jp.so", "_codecs_kr.so",
                 "_codecs_tw.so", "_contextvars.so", "_decimal.so", "_elementtree.so",
                 "_heapq.so", "_lsprof.so", "_lzma.so", "_md5.so",
                 "_multibytecodec.so", "_multiprocessing.so", "_opcode.so", "_pickle.so",
                 "_posixsubprocess.so", "_queue.so", "_sha1.so", "_sha256.so",
                 "_sha3.so", "_sha512.so", "_socket.so", "_sqlite3.so", "_ssl.so",
                 "_statistics.so", "_xxsubinterpreters.so", "_xxtestfuzz.so", "array.so",
                 "audioop.so", "cmath.so", "fcntl.so", "ossaudiodev.so", "parser.so",
                 "pyexpat.so", "resource.so", "select.so", "syslog.so", "termios.so",
                 "unicodedata.so", "xxlimited.so"],
                stdlib_native_zip.namelist())

        # build.json
        with open(join(asset_dir, "build.json")) as build_json_file:
            build_json = json.load(build_json_file)
        self.test.assertEqual(["assets"], sorted(build_json))
        asset_list = []
        for dirpath, dirnames, filenames in os.walk(asset_dir):
            asset_list += [relpath(join(dirpath, f), asset_dir).replace("\\", "/")
                           for f in filenames]
        self.test.assertEqual(
            {filename: file_sha1(join(asset_dir, filename))
             for filename in asset_list if filename != "build.json"},
            build_json["assets"])

    def check_lib(self, lib_dir, kwargs):
        abis = kwargs["abis"]
        self.test.assertCountEqual(abis, os.listdir(lib_dir))
        for abi in abis:
            self.test.assertCountEqual(
                ["libchaquopy_java.so", "libcrypto_chaquopy.so",
                 f"libpython{PYTHON_VERSION_SHORT}.so", "libssl_chaquopy.so",
                 "libsqlite3_chaquopy.so"],
                os.listdir(f"{lib_dir}/{abi}"))

    def dump_run(self, msg):
        self.test.fail(msg + "\n" +
                       "=== STDOUT ===\n" + self.stdout +
                       "=== STDERR ===\n" + self.stderr)


def file_sha1(filename):
    with open(filename, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()


# This is tested by Basic.test_kwargs_wrapper.
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


def dex_classes(apk_dir):
    build_tools_dir = join(sdk_dir, "build-tools")
    newest_ver = sorted(os.listdir(build_tools_dir))[-1]
    dexdump_cmd = f"{build_tools_dir}/{newest_ver}/dexdump"

    classes = {}
    file_num = 1
    while True:
        # Multidex is used by default in debug builds when minSdkVersion is 21 or higher
        # (https://developer.android.com/studio/build/multidex).
        dex_filename = f"{apk_dir}/classes{file_num if (file_num > 1) else ''}.dex"
        if exists(dex_filename):
            for line in run([dexdump_cmd, dex_filename], check=True, capture_output=True,
                            text=True).stdout.splitlines():
                match = re.search(r"Class descriptor *: *'L(.*);'", line)
                if match:
                    package, _, name = match[1].replace("/", ".").rpartition(".")
                    if not exclude_class(name):
                        classes.setdefault(package, []).append(name)
        else:
            break
        file_num += 1

    return classes


def jar_classes(zip_file):
    classes = {}
    for path in zip_file.namelist():
        if path.endswith(".class"):
            path = path.replace(".class", "")
            package, _, name = path.replace("/", ".").rpartition(".")
            if not exclude_class(name):
                classes.setdefault(package, []).append(name)
    return classes


def exclude_class(name):
    return ("$" in name) or (name in ["BuildConfig", "R"])


def chaquopy_classes():
    classes = {}
    for module in ["runtime", "buildSrc"]:
        java_dir = f"{repo_root}/product/{module}/src/main/java"
        for dirpath, dirnames, filenames in os.walk(java_dir):
            for name in filenames:
                if name.endswith(".java") and name != "package-info.java":
                    package = relpath(dirpath, java_dir).replace(os.sep, ".")
                    classes.setdefault(package, []).append(name.replace(".java", ""))
    return classes


def task_name(prefix, variant, suffix=""):
    # Differs from str.capitalize() because it only affects the first character
    def cap_first(s):
        return s if (s == "") else (s[0].upper() + s[1:])

    # Don't include the :app: prefix: the project may have multiple modules (e.g.
    # dynamic features or AARs).
    return (prefix +
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
