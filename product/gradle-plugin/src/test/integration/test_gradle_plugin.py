# This file requires the packages listed in requirements.txt.

from contextlib import contextmanager
from distutils import dir_util
from fnmatch import fnmatch
import hashlib
import json
import os
from os.path import abspath, basename, dirname, exists, isdir, join, relpath
import re
import shutil
import subprocess
from subprocess import run
import sys
from tempfile import TemporaryDirectory
from unittest import skipIf, skipUnless, TestCase
from zipfile import ZipFile, ZIP_STORED

import appdirs
from elftools.elf.elffile import ELFFile
from javaproperties import PropertiesFile
from retrying import retry


integration_dir = abspath(dirname(__file__))
data_dir = join(integration_dir, "data")
repo_root = abspath(join(integration_dir, "../../../../.."))
product_dir = f"{repo_root}/product"
plugin_dir = f"{product_dir}/gradle-plugin"
chaquopy_version = open(f"{repo_root}/VERSION.txt").read().strip()

# The following properties file should be created manually, as described in
# product/README.md. It's also used in runtime/build.gradle.
with open(f"{product_dir}/local.properties") as props_file:
    product_props = PropertiesFile.load(props_file)

DEFAULT_PYTHON_VERSION = "3.8"

def run_build_python(args, **kwargs):
    # The Gradle plugin's build script finds Python in the same way as the plugin
    # itself, so we can assume sys.executable is what the plugin will use.
    assert sys.version.startswith(DEFAULT_PYTHON_VERSION + ".")

    for k, v in dict(check=True, capture_output=True, text=True).items():
        kwargs.setdefault(k, v)
    return run([sys.executable] + args, **kwargs)

def list_versions(mode):
    return (run_build_python([f"{repo_root}/target/list-versions.py", f"--{mode}"])
            .stdout.strip())

assert list_versions("default") == DEFAULT_PYTHON_VERSION

PYTHON_VERSIONS = {}
for full_version in list_versions("micro").splitlines():
    version = full_version.rpartition(".")[0]
    PYTHON_VERSIONS[version] = full_version
assert list(PYTHON_VERSIONS) == ["3.8", "3.9", "3.10", "3.11", "3.12"]
DEFAULT_PYTHON_VERSION_FULL = PYTHON_VERSIONS[DEFAULT_PYTHON_VERSION]

NON_DEFAULT_PYTHON_VERSION = "3.10"
assert NON_DEFAULT_PYTHON_VERSION != DEFAULT_PYTHON_VERSION

BUILD_PYTHON_VERSION_FULL = (run_build_python(["--version"]).stdout  # e.g. "Python 3.7.1"
                             .split()[1])
BUILD_PYTHON_VERSION = BUILD_PYTHON_VERSION_FULL.rpartition(".")[0]

# When updating these, consider also updating .github/actions/setup-python/action.yml.
OLD_BUILD_PYTHON_VERSION = "3.6"
MIN_BUILD_PYTHON_VERSION = "3.7"
MAX_BUILD_PYTHON_VERSION = "3.12"

EGG_INFO_SUFFIX = "py" + BUILD_PYTHON_VERSION + ".egg-info"
EGG_INFO_FILES = ["dependency_links.txt", "PKG-INFO", "SOURCES.txt", "top_level.txt"]


# Android Gradle Plugin version (passed from Gradle task).
agp_version = os.environ["CHAQUOPY_AGP_VERSION"]
agp_version_info = tuple(map(int, agp_version.split(".")))

# This pattern causes Android Studio to show the line as a warning in tree view. However, the
# "Warning: " prefix will be removed, so the rest of the message should start with a capital
# letter.
WARNING = "^Warning: "


class GradleTestCase(TestCase):
    maxDiff = None

    def setUp(self):
        module, cls, func = re.search(r"^(\w+)\.(\w+)\.test_(\w+)$", self.id()).groups()
        self.run_dir = join(plugin_dir, "build/test/integration", agp_version, cls, func)

    def tearDown(self):
        # Remove build directory if test passed.
        if exists(self.run_dir) and not any(exc for _, exc in self._outcome.errors):
            rmtree(self.run_dir)

    def RunGradle(self, *args, **kwargs):
        return RunGradle(self, *args, **kwargs)

    # The version-numbered "base" layers differ in whether their top-level build.gradle
    # and settings.gradle files are in Kotlin or Groovy, so tests that provide their own
    # versions of these files should call this method to remove the base versions.
    def remove_root_gradle_files(self, run):
        for name in ["build", "settings"]:
            for ext in ["gradle", "gradle.kts"]:
                path = f"{run.project_dir}/{name}.{ext}"
                if exists(path):
                    os.remove(path)

    @contextmanager
    def setLongMessage(self, value):
        old_value = self.longMessage
        self.longMessage = value
        yield
        self.longMessage = old_value

    def assertInStdout(self, a, run, **kwargs):
        self.assertInLong(a, run.stdout,
                          msg="=== STDERR ===\n" + run.stderr, **kwargs)

    # WHen testing the stderr, there's usually no need to display the stdout.
    def assertInStderr(self, a, run, **kwargs):
        self.assertInLong(a, run.stderr, **kwargs)

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
    # If `pyc` is true and a filename ends with ".py", then a .pyc file will be expected
    # instead, unless the module is covered by `extract_packages`, in which case both
    # files will be expected.
    #
    # The content of .dist_info directories is ignored unless `include_dist_info` is true.
    # However, the *names* of .dist_info directories can be tested by passing `dist_versions`
    # as a list of (name, version) tuples.
    def checkZip(self, zip_filename, files, *, pyc=False, extract_packages=[],
                 include_dist_info=False, dist_versions=None):
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
                        if any(filename.startswith(ep.replace(".", "/") + "/")
                               for ep in extract_packages):
                            expected_files.append(filename)
                        filename += "c"
                    expected_files.append(filename)
                    try:
                        zip_info = zip_file.getinfo(filename)
                    except KeyError:
                        # It's more useful to report missing files in the actual_files
                        # check below.
                        pass
                    else:
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
    def test_groovy(self):
        run = self.RunGradle("base/groovy", run=False)
        self.check_before(run)
        run.rerun()
        self.check_after(run)

    def test_kotlin(self):
        run = self.RunGradle("base/kotlin", run=False)
        self.check_before(run)
        run.rerun()
        self.check_after(run)

    def check_before(self, run):
        src_dir = f"{run.project_dir}/app/src"
        self.assertEqual(
            list(os.walk(src_dir)),
            [
                (src_dir, ["main"], []),
                (join(src_dir, "main"), [], ["AndroidManifest.xml"]),
            ])

    def check_after(self, run):
        # Main source directory should be created automatically, to invite the user to
        # put things in it.
        src_dir = f"{run.project_dir}/app/src"
        self.assertEqual(
            list(os.walk(src_dir)),
            [
                (src_dir, ["main"], []),
                (join(src_dir, "main"), ["python"], ["AndroidManifest.xml"]),
                (join(src_dir, "main", "python"), [], []),
            ])

    def test_kwargs_wrapper(self):
        with self.assertRaisesRegex(AssertionError, "{'unused'} is not false"):
            self.RunGradle("base", unused=None)

    def test_variant(self):
        self.RunGradle("base", "Basic/variant", variants=["red-debug", "blue-debug"])


# Cover as much of the DSL as possible in a single test.
class Dsl(GradleTestCase):
    def test_groovy_old(self):
        self.check_dsl("base/groovy", "Dsl/groovy_old")

    def test_groovy_new(self):
        self.check_dsl("base/groovy", "Dsl/groovy_new")

    def test_kotlin(self):
        self.check_dsl("base/kotlin", "Dsl/kotlin")

    def check_dsl(self, *layers):
        run = self.RunGradle(
            *layers, "Dsl/common",
            variants={
                "property-debug": dict(
                    python_version="3.9",
                    extract_packages=[
                        "ep_default_property", "ep_default_method", "ep_property"],
                    app=[
                        "sp_property.py", "sp_method.py", "property.py", "ss_property.py"],
                    classes={"sp_property": ["PropertyProxy"]},
                    requirements=[f"certifi/{name}" for name in [
                        "__init__.py", "__main__.py", "cacert.pem", "core.py", "py.typed"
                    ]],
                    dist_versions=[("certifi", "2023.7.22")],
                    pyc=["src"],
                ),
                "method-debug": dict(
                    python_version="3.10",
                    extract_packages=[
                        "ep_default_property", "ep_default_method", "ep_method"],
                    app=[
                        "sp_property.py", "sp_method.py", "method.py", "ss_method.py"],
                    classes={"sp_method": ["MethodProxy"]},
                    requirements=["six.py"],
                    dist_versions=[("six", "1.15.0")],
                    pyc=["pip"],
                ),
            })

        run.rerun(variants=["bpProperty-debug"], succeed=False)
        self.assertInStderr(BuildPython.INVALID.format("python-property"), run)

        run.rerun(variants=["bpMethod-debug"], succeed=False)
        self.assertInStderr(BuildPython.INVALID.format("python-method"), run)


class ChaquopyPlugin(GradleTestCase):
    # Test the old "apply plugin" syntax.
    def test_apply(self):
        self.RunGradle("base", "ChaquopyPlugin/apply")

    # Make sure we still work if the plugin is applied in the app module buildscript rather
    # than the root project.
    def test_apply_buildscript(self):
        run = self.RunGradle("base", run=False)
        self.remove_root_gradle_files(run)
        run.rerun("ChaquopyPlugin/apply_buildscript")


class AndroidPlugin(GradleTestCase):
    ADVICE = ("Please edit the version of com.android.application, com.android.library or "
              "com.android.tools.build:gradle in your top-level build.gradle file. See "
              "https://chaquo.com/chaquopy/doc/current/versions.html.")

    # Now that we detect the Android plugin using pluginManager.withPlugin, misordering
    # is no longer a problem.
    def test_misordered(self):
        self.RunGradle("base", "AndroidPlugin/misordered")

    def test_missing(self):
        run = self.RunGradle("base", "AndroidPlugin/missing", succeed=False)
        self.assertInLong("Chaquopy requires one of the Android Gradle plugins. Please "
                          "apply one of the following plugins to ':app' project: "
                          "[com.android.application, com.android.library]",
                          run.stderr)

    def test_old(self):  # Also tests making a change
        MESSAGE = ("This version of Chaquopy requires Android Gradle plugin version "
                   "7.0.0 or later")
        run = self.RunGradle("base", run=False)
        self.remove_root_gradle_files(run)
        run.rerun("AndroidPlugin/old", succeed=False)
        self.assertInLong(f"{MESSAGE}. {self.ADVICE}", run.stderr)

        self.remove_root_gradle_files(run)
        run.rerun("base")
        self.assertNotInLong(MESSAGE, run.stderr)


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

    MULTI_MESSAGE = r"(More than one file was|2 files) found"

    def test_multi_lib(self):
        if agp_version_info < (7, 3):
            run = self.RunGradle("base", "Aar/multi_lib", succeed=False)
            self.assertInLong(self.MULTI_MESSAGE, run.stderr, re=True)
        else:
            # Newer AGP versions silently use the assets from the first lib.
            run = self.RunGradle("base", "Aar/multi_lib", app=["lib1.py"])
            for stream in [run.stdout, run.stderr]:
                self.assertNotInLong(self.MULTI_MESSAGE, stream, re=True)

    def test_lib_and_app(self):
        # The assets from the app are used.
        run = self.RunGradle("base", "Aar/lib_and_app", app=["app.py"])
        if agp_version_info < (7, 3):
            self.assertInLong(self.MULTI_MESSAGE + r".* Future versions of the Android Gradle "
                              "Plugin (will|may) throw an error in this case.",
                              run.stdout, re=True)
        else:
            # Newer AGP versions no longer show a warning.
            for stream in [run.stdout, run.stderr]:
                self.assertNotInLong(self.MULTI_MESSAGE, stream, re=True)

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
    ERROR = ("This version of Chaquopy requires minSdk version 21 or higher. "
             "See https://chaquo.com/chaquopy/doc/current/versions.html.")

    def test_minimum(self):  # Also tests making a change
        run = self.RunGradle("base", "ApiLevel/minimum")
        run.apply_layers("ApiLevel/old")
        run.rerun(succeed=False)
        self.assertInLong("Variant 'debug': " + self.ERROR, run.stderr)

    def test_variant(self):
        run = self.RunGradle("base", "ApiLevel/variant", succeed=False)
        self.assertInLong("Variant 'redDebug': " + self.ERROR, run.stderr)


class JavaLib(GradleTestCase):

    # The Chaquopy plugin can't be used directly within a dynamic feature module, but if it's
    # used in the base module, then the Java API should be available to the feature module.
    def test_dynamic_feature(self):
        self.RunGradle("base", "JavaLib/dynamic_feature")

    # See also Aar.test_minify.
    def test_minify(self):
        self.RunGradle("base", "JavaLib/minify")

    def test_minify_variant(self):
        self.RunGradle("base", "JavaLib/minify_variant",
                       variants={"blue-debug": dict(classes={"com.example": ["Blue"]}),
                                 "red-debug":  dict(classes={"com.example": ["Red"]})})


class PythonVersion(GradleTestCase):
    WARNING = (WARNING + "Python version {} may have fewer packages available. "
               "If you experience problems, try switching to version " +
               DEFAULT_PYTHON_VERSION + ".")

    # To allow a quick check of the setting, this test only covers two versions.
    def test_change(self):
        run = self.RunGradle("base", run=False)
        for version in [DEFAULT_PYTHON_VERSION, NON_DEFAULT_PYTHON_VERSION]:
            self.check_version(run, version)

    # Test all versions not covered by test_change.
    def test_others(self):
        run = self.RunGradle("base", run=False)
        for version in PYTHON_VERSIONS:
            if version not in [DEFAULT_PYTHON_VERSION, NON_DEFAULT_PYTHON_VERSION]:
                self.check_version(run, version)

    def check_version(self, run, version):
        with self.subTest(version=version):
            # Make sure every ABI has the full set of native stdlib module files.
            abis = ["arm64-v8a", "x86_64"]
            if version in ["3.8", "3.9", "3.10", "3.11"]:
                abis += ["armeabi-v7a", "x86"]
            run.rerun(f"PythonVersion/{version}", python_version=version, abis=abis)

            if version == DEFAULT_PYTHON_VERSION:
                self.assertNotInLong(self.WARNING.format(".*"), run.stdout, re=True)
            else:
                self.assertInLong(self.WARNING.format(version), run.stdout, re=True)

    def test_variant(self):
        self.RunGradle("base", "PythonVersion/variant",
                       variants={"alpha-one-debug": dict(python_version="3.8"),
                                 "alpha-two-debug": dict(python_version="3.10"),
                                 "bravo-one-debug": dict(python_version="3.9"),
                                 "bravo-two-debug": dict(python_version="3.9")})

    def test_invalid(self):
        ERROR = ("Invalid Python version '{}'. Available versions are [" +
                 ", ".join(PYTHON_VERSIONS) + "].")
        run = self.RunGradle("base", "PythonVersion/invalid", succeed=False)
        self.assertInLong(ERROR.format("invalid"), run.stderr)

        run.apply_layers("PythonVersion/invalid_micro")
        run.rerun(succeed=False)
        self.assertInLong(ERROR.format("3.8.13"), run.stderr)


class AbiFilters(GradleTestCase):
    def test_missing(self):
        run = self.RunGradle("base", "AbiFilters/missing", succeed=False)
        self.assertInLong("Variant 'debug': Chaquopy requires ndk.abiFilters",
                          run.stderr)

    def test_invalid(self):
        run = self.RunGradle("base", "AbiFilters/invalid", succeed=False)
        self.assertInLong(
            "Variant 'debug': Python 3.8 is not available for the ABI 'armeabi'. "
            "Supported ABIs are [arm64-v8a, armeabi-v7a, x86, x86_64].",
            run.stderr)

    def test_invalid_32bit(self):
        run = self.RunGradle("base", "AbiFilters/invalid_32bit", succeed=False)
        self.assertInLong(
            "Variant 'debug': Python 3.12 is not available for the ABI 'x86'. "
            "Supported ABIs are [arm64-v8a, x86_64].",
            run.stderr)

    def test_all(self):  # Also tests making a change.
        run = self.RunGradle("base", abis=["x86"])

        # Add ABIs
        run.rerun("AbiFilters/all", abis=["armeabi-v7a", "arm64-v8a", "x86", "x86_64"])

        # Remove ABIs
        run.rerun("base", abis=["x86"])

    def test_variant(self):
        self.RunGradle(
            "base", "AbiFilters/variant",
            variants={"alpha-one-debug": dict(abis=["x86"]),
                      "alpha-two-debug": dict(abis=["x86", "arm64-v8a"]),
                      "bravo-one-debug": dict(abis=["x86", "armeabi-v7a"]),
                      "bravo-two-debug": dict(abis=["x86", "armeabi-v7a", "arm64-v8a"])})

    def test_variant_missing(self):
        run = self.RunGradle("base", "AbiFilters/variant_missing", succeed=False)
        self.assertInLong("Variant 'missingDebug': Chaquopy requires ndk.abiFilters",
                          run.stderr)


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
        common_py = ("common.py", {"content": "common main"})
        kwargs = dict(
            pyc=["stdlib"],
            variants={
                "red-debug": dict(app=[common_py, ("color.py", {"content": "red"})]),
                "blue-debug": dict(app=[common_py, ("color.py", {"content": "blue"})])
            })

        run = self.RunGradle("base", "PythonSrc/conflict", succeed=False, **kwargs)
        self.assertInStderr(self.conflict_error("BlueDebug", "common.py"), run, re=True)

        run.rerun("PythonSrc/conflict_exclude", **kwargs)
        run.rerun("PythonSrc/conflict_include", **kwargs)

    def conflict_error(self, variant, filename):
        return (
            fr"(?s)failed for task ':app:merge{variant}PythonSources'.*" + (
                fr'Encountered duplicate path "{filename}"'
                if agp_version_info < (8, 5)

                # No leading quote, because the message includes the full path.
                else fr"{filename}' has already been copied there"
            )
        )

    def test_set_dirs(self):
        self.RunGradle("base", "PythonSrc/set_dirs", app=["two.py"])

    def test_multi_dir(self):
        self.RunGradle("base", "PythonSrc/multi_dir", app=["one.py", "two.py"])

    def test_multi_dir_conflict(self):
        run = self.RunGradle("base", "PythonSrc/multi_dir_conflict", succeed=False)
        self.assertInStderr(self.conflict_error("Debug", "one.py"), run, re=True)

    def test_multi_dir_conflict_empty(self):
        self.RunGradle("base", "PythonSrc/multi_dir_conflict_empty",
                       app=["one.py", "two.py", "empty.py"])


class ExtractPackages(GradleTestCase):
    def test_change(self):
        # This directory is also installed by the demo app for use in TestAndroidImport.
        PY_FILES = [
            f"{pkg}/{path}"
            for pkg in ["ep_alpha", "ep_bravo", "ep_charlie"]
            for path in ["__init__.py", "mod.py", "one/__init__.py", "two/__init__.py"]
        ]
        kwargs = dict(app=PY_FILES, requirements=PY_FILES)
        run = self.RunGradle("base", "ExtractPackages/change_1", **kwargs)
        run.rerun("ExtractPackages/change_2",
                  extract_packages=["ep_bravo", "ep_charlie.one"], **kwargs)

    def test_variant(self):
        self.RunGradle("base", "ExtractPackages/variant",
                       app=["red/__init__.py", "blue/__init__.py"],
                       variants={"red-debug": dict(extract_packages=["red"]),
                                 "blue-debug": dict(extract_packages=["blue"])})

    def test_variant_merge(self):
        self.RunGradle("base", "ExtractPackages/variant_merge",
                       app=["common/__init__.py", "red/__init__.py", "blue/__init__.py"],
                       variants={"red-debug": dict(extract_packages=["common"]),
                                 "blue-debug": dict(extract_packages=["common", "blue"])})


class Pyc(GradleTestCase):
    FAILED = "Failed to compile to .pyc format: "
    INCOMPATIBLE = fr"buildPython version {NON_DEFAULT_PYTHON_VERSION}.\d+ is incompatible. "
    SEE = "See https://chaquo.com/chaquopy/doc/current/android.html#android-bytecode"

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

    def test_buildpython_warning(self):
        run = self.RunGradle("base", "Pyc/buildpython_warning", pyc=["stdlib"])
        self.assertInStdout(
            WARNING + self.FAILED +
            re.escape(BuildPython.INVALID.format("pythoninvalid")) + self.SEE,
            run, re=True)

        run.apply_layers("Pyc/buildpython_warning_suppress")
        run.rerun(pyc=["stdlib"])
        self.assertNotInLong(self.FAILED, run.stdout)

    def test_buildpython_error(self):
        run = self.RunGradle("base", "Pyc/buildpython_error", succeed=False)
        self.assertInStderr(
            BuildPython.INVALID.format("pythoninvalid") + BuildPython.SEE, run)

    def test_buildpython_missing_warning(self):
        run = self.RunGradle(
            "base", "Pyc/buildpython_missing_warning", "BuildPython/missing",
            add_path=["bin"])
        self.assertInStdout(
            WARNING + self.FAILED + BuildPython.MISSING + self.SEE,
            run, re=True)

    def test_buildpython_missing_error(self):
        run = self.RunGradle(
            "base", "Pyc/buildpython_missing_error", "BuildPython/missing",
            add_path=["bin"], succeed=False)
        self.assertInStderr(BuildPython.MISSING + BuildPython.SEE, run)

    def test_magic_warning(self):
        run = self.RunGradle("base", "Pyc/magic_warning",
                             env={"buildpython_version": NON_DEFAULT_PYTHON_VERSION},
                             requirements=["six.py"], pyc=["stdlib"])
        self.assertInStdout(WARNING + self.FAILED + self.INCOMPATIBLE + self.SEE,
                            run, re=True)

    def test_magic_error(self):
        run = self.RunGradle("base", "Pyc/magic_error",
                             env={"buildpython_version": NON_DEFAULT_PYTHON_VERSION},
                             succeed=False)
        self.assertInStderr(self.FAILED + self.INCOMPATIBLE + self.SEE, run, re=True)
        self.assertInStderr(BuildPython.FAILED, run, re=True)


class BuildPython(GradleTestCase):
    # Some of these messages are also used in other test classes.
    SEE = "See https://chaquo.com/chaquopy/doc/current/android.html#buildpython"
    MISSING = "Couldn't find Python. "
    INVALID = "[{}] does not appear to be a valid Python command. "
    FAILED = (r"Process 'command '.+'' finished with non-zero exit value 1 \n\n"
              r"To view full details in Android Studio:\n"
              r"\* Click the 'Build: failed' caption to the left of this message.\n"
              r"\* Then scroll up to see the full output.")

    @classmethod
    def old_version_error(cls):
        return (fr"buildPython must be version {MIN_BUILD_PYTHON_VERSION} or later: "
                fr"this is version {OLD_BUILD_PYTHON_VERSION}\.\d+\. " + cls.SEE)

    # Default buildPython depends on selected Python version.
    def test_default(self):
        run = self.RunGradle("base", "BuildPython/default", add_path=["bin"], succeed=False)
        self.assertInStdout("3.8 was used", run)
        self.assertNotInLong("3.9 was used", run.stdout)

        run.apply_layers("BuildPython/default_3.9")
        run.rerun(add_path=["bin"], succeed=False)
        self.assertNotInLong("3.8 was used", run.stdout)
        self.assertInStdout("3.9 was used", run)

        # Default can be overridden.
        run.apply_layers("BuildPython/default_3.9_override")
        run.rerun(add_path=["bin"], succeed=False)
        self.assertInStdout("3.8 was used", run)
        self.assertNotInLong("3.9 was used", run.stdout)

    def test_args(self):  # Also tests making a change.
        run = self.RunGradle("base", "BuildPython/args_1", succeed=False)
        self.assertInStdout("echo_args1", run)
        run.apply_layers("BuildPython/args_2")
        run.rerun(succeed=False)
        self.assertInStdout("echo_args2", run)

    def test_space(self):
        run = self.RunGradle("base", "BuildPython/space", succeed=False)
        self.assertInStdout("Hello Chaquopy", run)

    # test_missing was replaced with one test_buildpython_missing method for each task
    # that uses buildPython.

    def test_missing_minor(self):
        run = self.RunGradle("base", "BuildPython/missing_minor", add_path=["bin"],
                             succeed=False)
        self.assertNotInLong("Minor version was used", run.stdout)
        self.assertInStdout("Major version was used", run)
        self.assertNotInLong("Versionless executable was used", run.stdout)

    def test_missing_major(self):
        run = self.RunGradle("base", "BuildPython/missing_major", add_path=["bin"],
                             succeed=False)
        self.assertInStdout("Minor version was used", run)
        self.assertNotInLong("Major version was used", run.stdout)
        self.assertNotInLong("Versionless executable was used", run.stdout)

    def test_missing_both(self):
        run = self.RunGradle("base", "BuildPython/missing_both", add_path=["bin"],
                             succeed=False)
        self.assertNotInLong("Minor version was used", run.stdout)
        self.assertNotInLong("Major version was used", run.stdout)
        self.assertInStdout("Versionless executable was used", run)

    # Test a buildPython which returns success without doing anything (possibly the
    # cause of #250).
    def test_silent_failure(self):
        run = self.RunGradle("base", "BuildPython/silent_failure", succeed=False)
        lib_path = "python/env/debug/lib"
        if os.name == "nt":
            lib_path = lib_path.replace("/", "\\").replace("lib", "Lib")
        self.assertInStderr(f"{lib_path} does not exist", run)

    def test_variant(self):
        run = self.RunGradle("base", "BuildPython/variant", variants=["red-debug"],
                             succeed=False)
        self.assertInStderr(self.INVALID.format("python-red") + self.SEE, run)
        run.rerun(variants=["blue-debug"], succeed=False)
        self.assertInStderr(self.INVALID.format("python-blue"), run)

    def test_variant_merge(self):
        run = self.RunGradle("base", "BuildPython/variant_merge", variants=["red-debug"],
                             succeed=False)
        self.assertInStderr(self.INVALID.format("python-red") + self.SEE, run)
        run.rerun(variants=["blue-debug"], succeed=False)
        self.assertInStderr(self.INVALID.format("python-blue") + self.SEE, run)


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

    # https://github.com/chaquo/chaquopy/issues/468
    @skipUnless(os.name == "posix", "Requires symlink support")
    def test_symlink(self):
        run = self.RunGradle("base", "PythonReqs/1a", run=False)
        link_path = f"{run.project_dir}/app"
        real_path = f"{run.project_dir}/subdir/app"
        os.renames(link_path, real_path)
        os.symlink(real_path, link_path)
        run.rerun(requirements=["apple/__init__.py"])

    def test_buildpython(self):
        # Use a fresh RunGradle instance for each test in order to clear the pip cache.
        layers = ["base", "PythonReqs/buildpython"]

        for version in [MIN_BUILD_PYTHON_VERSION, MAX_BUILD_PYTHON_VERSION]:
            with self.subTest(version=version):
                self.RunGradle(*layers, env={"buildpython_version": version},
                               requirements=["apple/__init__.py",
                                             "no_binary_sdist/__init__.py",
                                             "six.py"],
                               pyc=["stdlib"])

        run = self.RunGradle(*layers, env={"buildpython_version": OLD_BUILD_PYTHON_VERSION},
                             succeed=False)
        self.assertInLong(BuildPython.old_version_error(), run.stderr, re=True)

    def test_buildpython_missing(self):
        run = self.RunGradle(
            "base", "PythonReqs/buildpython_missing", "BuildPython/missing",
            add_path=["bin"], succeed=False)
        self.assertInLong(BuildPython.MISSING + BuildPython.SEE, run.stderr)

    def test_download_wheel(self):
        # Our current version of pip shows the full URL for custom indexes, but only
        # the filename for PyPI.
        CHAQUO_URL = (r"https://chaquo.com/pypi-13.1/murmurhash/"
                      r"murmurhash-0.28.0-7-cp38-cp38-android_16_x86.whl")
        PYPI_URL = "six-1.14.0-py2.py3-none-any.whl"

        common_reqs = (["murmurhash/" + name for name in
                        ["__init__.pxd", "__init__.py", "about.py", "mrmr.pxd", "mrmr.pyx",
                         "include/murmurhash/MurmurHash2.h", "include/murmurhash/MurmurHash3.h",
                         "tests/__init__.py", "tests/test_import.py"]] +
                       ["chaquopy_libcxx-11000.dist-info/" + name for name in
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

    # Some sdists with optional native components generate a wheel tagged with the build
    # platform even when the native components are omitted. This test checks that the wheel is
    # cached and reused on subsequent runs of pip, even if the ABI is different.
    def test_download_sdist(self):
        FILENAME = "PyYAML-3.12.tar.gz"
        BUILD = "Successfully built PyYAML"
        REQS = ["yaml/" + name + ".py" for name in
                ["__init__", "composer", "constructor", "cyaml", "dumper", "emitter", "error",
                 "events", "loader", "nodes", "parser", "reader", "representer", "resolver",
                 "scanner", "serializer", "tokens"]]
        run = self.RunGradle("base", "PythonReqs/download_sdist_1", requirements=REQS)
        self.assertInLong("Downloading " + FILENAME, run.stdout, re=True)
        self.assertInLong(BUILD, run.stdout)

        run.apply_layers("PythonReqs/download_sdist_2")
        run.rerun(requirements=REQS, abis=["armeabi-v7a"])
        # pip prints lots of detail when it puts a wheel into the cache, but says absolutely
        # nothing when it takes one out.
        self.assertNotInLong(FILENAME, run.stdout, re=True)
        self.assertNotInLong(BUILD, run.stdout)

    # Test the OpenSSL PATH workaround for conda on Windows. This is not necessary on
    # Linux because conda uses RPATH on that platform, and I think it's similar on Mac.
    @skipUnless(os.name == "nt", "Windows only")
    def test_conda(self):
        # Remove PATH entries which contain any copy of libssl. If it's installed in
        # C:\Windows\System32 or some other critical directory, then this test will probably
        # fail.
        path = os.pathsep.join(
            entry for entry in os.environ["PATH"].split(os.pathsep)
            if isdir(entry) and not any(fnmatch(filename, "libssl*.dll")
                                        for filename in os.listdir(entry)))
        self.RunGradle("base", "PythonReqs/conda",
                       env={"chaquopy_conda_env": product_props["chaquopy.conda.env"],
                            "PATH": path},
                       requirements=["six.py"], pyc=["stdlib"])

    ISOLATED_KWARGS = dict(
        dist_versions=[("six", "1.14.0"), ("build_requires_six", "1.14.0")],
        requirements=["six.py"])

    # `PIP_...` environment variables should have no effect.
    def test_isolated_env(self):
        self.RunGradle("base", "PythonReqs/isolated",
                       env={"PIP_CERT": "invalid"},
                       **self.ISOLATED_KWARGS)

    # Pip configuration files should have no effect.
    def test_isolated_config(self):
        config_filename = join(appdirs.user_config_dir("pip", appauthor=False, roaming=True),
                               "pip.ini" if (os.name == "nt") else "pip.conf")
        config_backup = f"{config_filename}.{os.getpid()}"
        os.makedirs(dirname(config_filename), exist_ok=True)
        if exists(config_filename):
            os.replace(config_filename, config_backup)
        try:
            with open(config_filename, "x") as config_file:
                print("[global]\n"
                      "cert = invalid",
                      file=config_file)
            self.RunGradle("base", "PythonReqs/isolated", **self.ISOLATED_KWARGS)
        finally:
            if exists(config_filename):
                os.remove(config_filename)
            if exists(config_backup):
                os.replace(config_backup, config_filename)

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

    def test_directory(self):
        run = self.RunGradle("base", "PythonReqs/directory_1", requirements=["alpha1.py"])

        # Modify setup.py
        self.clean_package(run, "alpha")
        run.rerun("PythonReqs/directory_2", requirements=["bravo1.py"])

        # Add file
        run.rerun("PythonReqs/directory_3", requirements=["bravo1.py", "bravo2.py"])

        # Remove file
        self.clean_package(run, "alpha")
        os.remove(f"{run.project_dir}/app/alpha/bravo1.py")
        run.rerun(requirements=["bravo2.py"])

    # Work around https://github.com/pypa/setuptools/issues/1871.
    def clean_package(self, run, path):
        rmtree(f"{run.project_dir}/app/{path}/build/lib")

    def test_reqs_file(self):
        run = self.RunGradle("base", "PythonReqs/reqs_file",
                             requirements=["apple/__init__.py", "bravo/__init__.py"])
        run.apply_layers("PythonReqs/reqs_file_2")
        run.rerun(requirements=["alpha/__init__.py", "alpha_dep/__init__.py",
                                "bravo/__init__.py"])

    # This is a combination of test_directory and test_wheel_file, but installing
    # everything via a requirements file.
    def test_reqs_file_content(self):
        run = self.RunGradle("base", "PythonReqs/reqs_file_content_1",
                             requirements=["apple/__init__.py", "alpha1.py"])

        # Modify setup.py.
        self.clean_package(run, "alpha")
        run.rerun("PythonReqs/reqs_file_content_2",
                  requirements=["apple/__init__.py", "bravo1.py"])

        # Modify .whl file.
        run.rerun("PythonReqs/reqs_file_content_3",
                  requirements=["apple2/__init__.py", "bravo1.py"])

    def test_wheel_file_relative(self):
        run = self.RunGradle("base", "PythonReqs/wheel_file_relative",
                             "PythonReqs/wheel_file_1",
                             requirements=["apple/__init__.py"])
        run.rerun("PythonReqs/wheel_file_2", requirements=["apple2/__init__.py"])

    def test_wheel_file_absolute(self):
        run = self.RunGradle("base", "PythonReqs/wheel_file_absolute",
                             "PythonReqs/wheel_file_1",
                             requirements=["apple/__init__.py"])
        run.rerun("PythonReqs/wheel_file_2", requirements=["apple2/__init__.py"])

    # This wheel has .data subdirectories for each of the possible distutils scheme keys. Only
    # purelib and platlib should be included in the APK.
    def test_wheel_data(self):
        self.RunGradle("base", "PythonReqs/wheel_data",
                       requirements=["purelib.txt", "platlib.txt"])

    def test_sdist_file(self):
        self.RunGradle("base", "PythonReqs/sdist_file", requirements=["alpha_dep/__init__.py"])

    # These tests install a package with a native build requirement in its pyproject.toml,
    # which is used to generate the package's version number. This verifies that the build
    # environment is installed for the build platform, not the target platform.
    PEP517_KWARGS = dict(dist_versions=[("pep517", "2324772522")])

    def test_pep517_default_backend(self):
        self.RunGradle("base", "PythonReqs/pep517", "PythonReqs/pep517_default_backend",
                       **self.PEP517_KWARGS)

    def test_pep517_explicit_backend(self):
        self.RunGradle("base", "PythonReqs/pep517", "PythonReqs/pep517_explicit_backend",
                       **self.PEP517_KWARGS)

    # Test pip can handle TOML 1.0 syntax (e.g.
    # https://github.com/zeromq/pyzmq/issues/1807).
    def test_pep517_toml_1_0(self):
        self.RunGradle("base", "PythonReqs/pep517", "PythonReqs/pep517_toml_1_0",
                       **self.PEP517_KWARGS)

    def test_pep517_backend_path(self):
        self.RunGradle("base", "PythonReqs/pep517", "PythonReqs/pep517_backend_path",
                       **self.PEP517_KWARGS)

    # An alternative backend, with setuptools not installed in the build environment.
    def test_pep517_hatch(self):
        self.RunGradle(
            "base", "PythonReqs/pep517_hatch",
            dist_versions=[("pep517_hatch", "5.1.7")],
            requirements=["hatch1.py"])

    # Make sure we're not affected by a setup.cfg file containing a `prefix` line.
    def test_cfg_wheel(self):
        self.RunGradle("base", "PythonReqs/cfg_wheel", requirements=["apple/__init__.py"])

    # We need to fall back on setup.py install to test this, because bdist_wheel doesn't use
    # --prefix or --home.
    def test_cfg_sdist(self):
        run = self.RunGradle("base", "PythonReqs/cfg_sdist",
                             requirements=["bdist_wheel_fail/__init__.py"])
        self.assertInLong("Failed to build bdist-wheel-fail", run.stdout)
        self.assertInLong(self.RUNNING_INSTALL, run.stdout)

    # Check that pip builds source directories in place, not in a temporary directory.
    # For example, this is required by setuptools-scm.
    def test_sdist_in_place(self):
        self.RunGradle("base", "PythonReqs/sdist_in_place",
                       dist_versions=[("sdist_in_place", "1.2.3")])

    # By checking that this string is output in tests which fall back on setup.py install, we
    # can use the absence of the string in other tests to prove that no fallback occurred.
    RUNNING_INSTALL = "Running setup.py install"

    def test_sdist_native_ext(self):
        self.sdist_native("sdist_native_ext")

    def test_sdist_native_clib(self):
        self.sdist_native("sdist_native_clib")

    def test_sdist_native_compiler(self):
        self.sdist_native("sdist_native_compiler")

    def test_sdist_native_cc(self):
        self.sdist_native("sdist_native_cc")

    def sdist_native(self, name):
        for pep517 in [True, False]:
            with self.subTest(pep517=pep517):
                layers = ["base", f"PythonReqs/{name}"]
                if pep517:
                    layers.append("PythonReqs/sdist_native_pep517")
                run = self.RunGradle(*layers, succeed=False)

                if name == "sdist_native_cc":
                    setup_error = "Failed to run Chaquopy_cannot_compile_native_code"
                else:
                    setup_error = "Chaquopy cannot compile native code"
                self.assertInLong(setup_error, run.stderr)

                # If bdist_wheel fails with a "native code" message, we should not fall back on
                # setup.py install.
                self.assertNotInLong(self.RUNNING_INSTALL, run.stdout)

                url = r"file:.*app/sdist_native"
                if name in ["sdist_native_compiler", "sdist_native_cc"]:
                    # These tests fail at the egg_info stage, so the name and version
                    # are unavailable.
                    req_str = url
                else:
                    # These tests fail at the bdist_wheel stage, so the name and version
                    # have been obtained from egg_info. But how the name is formatted
                    # depends on whether we're using our bundled version of setuptools,
                    # or the current one from PyPI.
                    name_str = name if pep517 else name.replace('_', '-')
                    req_str = f"{name_str}==1.0 from {url}"
                self.assertInLong(fr"Failed to install {req_str}." +
                                  self.tracker_advice() + r"$", run.stderr, re=True)

    def test_sdist_native_optional_ext(self):
        self.sdist_native_optional("sdist_native_optional_ext")

    def test_sdist_native_optional_compiler(self):
        self.sdist_native_optional("sdist_native_optional_compiler")

    def sdist_native_optional(self, name):
        for pep517 in [True, False]:
            with self.subTest(pep517=pep517):
                layers = ["base", f"PythonReqs/{name}"]
                if pep517:
                    layers.append("PythonReqs/sdist_native_pep517")
                self.RunGradle(*layers, requirements=[f"{name}.py"])

    # If bdist_wheel fails without a "native code" message, we should fall back on setup.py
    # install (e.g. https://github.com/python-acoustics/python-acoustics/issues/243).
    def test_bdist_wheel_fail(self):
        run = self.RunGradle(
            "base", "PythonReqs/bdist_wheel_fail", include_dist_info=True,
            requirements=([f"bdist_wheel_fail-1.0-{EGG_INFO_SUFFIX}/{name}"
                           for name in EGG_INFO_FILES] +
                          ["bdist_wheel_fail/__init__.py"]))
        self.assertInLong("bdist_wheel throwing exception", run.stderr)
        self.assertInLong("Failed to build bdist-wheel-fail", run.stdout)
        self.assertInLong(self.RUNNING_INSTALL, run.stdout)

    # If bdist_wheel returns success but didn't generate a wheel, we should fall back on
    # setup.py install (e.g. #338).
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
        self.assertInLong(f"No module named '{PKG_NAME}'", run.stderr)

    def test_editable(self):
        run = self.RunGradle("base", "PythonReqs/editable", succeed=False)
        self.assertInLong("Invalid pip install format: [-e, src]", run.stderr)

    # This is not necessarily the ideal behavior, but it's the current behavior, slightly
    # modified by a patch (https://github.com/pypa/pip/issues/5846).
    def test_index_url(self):
        kwargs = dict(requirements=["six.py"])

        # With a file: URL, pip looks for an index.html file, and ignores all other files.
        run = self.RunGradle("base", "PythonReqs/index_url_file",
                             dist_versions=[("six", "1.12.0")], **kwargs)

        # With a simple path, pip scans the directory and ignores any index.html file.
        # This was enabled by a patch.
        run.rerun("PythonReqs/index_url_path",
                  dist_versions=[("six", "1.14.0")], **kwargs)

        # For completeness, check an HTTP index URL as well.
        run.rerun("PythonReqs/index_url_http",
                  dist_versions=[("six", "1.16.0")], **kwargs)

    def test_wheel_index(self):
        # This test has build platform wheels for version 0.2, and an Android wheel for version
        # 0.1, to test that pip always picks the target platform, not the workstation platform.
        self.check_build_platform_wheel("native1", "0.2")
        run = self.RunGradle("base", "PythonReqs/wheel_index_1",
                             dist_versions=[("native1", "0.1")],
                             requirements=["native1_android_15_x86/__init__.py"])

        # This test only has build platform wheels.
        self.check_build_platform_wheel("native2", "0.2")
        run.apply_layers("PythonReqs/wheel_index_2")
        run.rerun(succeed=False)
        self.assertInLong("No matching distribution found for native2", run.stderr)

    # Checks that when pip is installing for the build platform, it selects the given
    # version of the given package. This requires the platform to have a compatible wheel
    # in packages/dist.
    def check_build_platform_wheel(self, package, version):
        with TemporaryDirectory() as tmp_dir:
            plugin_src = f"{plugin_dir}/src/main/python"
            self.assertTrue(exists(f"{plugin_src}/pip"))
            subprocess.run(
                [sys.executable, "-m", "pip", "--quiet", "install", "--target", tmp_dir,
                 "--no-index", "--find-links", f"{integration_dir}/packages/dist",
                 package],
                env={**os.environ, "PYTHONPATH": plugin_src}, check=True)
            self.assertCountEqual(
                [f"{package}-{version}.dist-info"],
                [name for name in os.listdir(tmp_dir) if name.endswith(".dist-info")])

    # This package has wheels tagged as API levels 22 and 24, with corresponding
    # version numbers. Which one is selected should depend on the app's minSdkVersion.
    def test_api_level(self):
        run = self.RunGradle("base", run=False)
        for min_api_level, expected_version in [
            (21, None), (22, 22), (23, 22), (24, 24), (25, 24)
        ]:
            if expected_version:
                kwargs = dict(dist_versions=[("api_level", f"1.{expected_version}")],
                              abis=["arm64-v8a"])
            else:
                kwargs = dict(succeed=False)
            run.rerun(f"PythonReqs/api_level_{min_api_level}", **kwargs)
            if not expected_version:
                self.assertInLong("No matching distribution found for api_level",
                                  run.stderr)

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

        # With "!=1.3", the sdist is selected, but it will fail at the egg_info stage. (Failure
        # at later stages is covered by test_sdist_native.) Version 1.8 has two build numbers
        # available, but should only be listed once in the message.
        run.apply_layers("PythonReqs/mixed_index_2")
        run.rerun(succeed=False)
        self.assertInLong(
            r"Failed to install native3!=1.3 from file:.*dist/native3-2.0.tar.gz."
            + self.tracker_advice() + r"$",
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

    def test_no_binary_succeed(self):
        run = self.RunGradle("base", "PythonReqs/no_binary_succeed",
                             requirements=["no_binary_sdist/__init__.py"])
        self.assertInLong("Skipping wheel build", run.stdout)
        self.assertInLong(self.RUNNING_INSTALL, run.stdout)

    def test_requires_python(self):
        self.assertNotEqual(BUILD_PYTHON_VERSION_FULL, DEFAULT_PYTHON_VERSION_FULL)
        run = self.RunGradle("base", "PythonReqs/requires_python", run=False)
        with open(f"{run.project_dir}/app/index/pyver/index.html", "w") as index_file:
            def print_link(whl_version, requires_python):
                filename = f"pyver-{whl_version}-py2.py3-none-any.whl"
                print(f'<a href="{filename}" data-requires-python="=={requires_python}">'
                      f'{filename}</a><br/>', file=index_file)

            # If the build Python version is used, or the data-requires-python attribute is
            # ignored completely, then version 0.2 will be selected.
            print("<html><head></head><body>", file=index_file)
            print_link("0.1", DEFAULT_PYTHON_VERSION_FULL)
            print_link("0.2", BUILD_PYTHON_VERSION_FULL)
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
        self.assertNotEqual(BUILD_PYTHON_VERSION_FULL, DEFAULT_PYTHON_VERSION_FULL)
        run = self.RunGradle("base", "PythonReqs/marker_python_version", run=False)
        with open(f"{run.project_dir}/app/requirements.txt", "w") as reqs_file:
            def print_req(whl_version, python_version):
                print(f'pyver-{whl_version}-py2.py3-none-any.whl; '
                      f'python_full_version == "{python_version}"', file=reqs_file)

            # If the build Python version is used, or the environment markers are ignored
            # completely, then version 0.2 will be selected.
            print_req("0.1", DEFAULT_PYTHON_VERSION_FULL)
            print_req("0.2", BUILD_PYTHON_VERSION_FULL)

        run.rerun(requirements=["pyver.py"], dist_versions=[("pyver", "0.1")])

    def tracker_advice(self):
        return ("\nFor assistance, please raise an issue at "
                "https://github.com/chaquo/chaquopy/issues.")


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

        run = self.RunGradle(*layers, env={"buildpython_version": OLD_BUILD_PYTHON_VERSION},
                             succeed=False)
        self.assertInLong(BuildPython.old_version_error(), run.stderr, re=True)

    def test_buildpython_missing(self):
        run = self.RunGradle(
            "base", "StaticProxy/buildpython_missing", "BuildPython/missing",
            add_path=["bin"], succeed=False)
        self.assertInLong(BuildPython.MISSING + BuildPython.SEE, run.stderr)

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
    # With AGP 8.0 on Windows, the full test run sometimes causes OutOfMemoryErrors.
    # Editing gradle.properties to increase -Xmx to 4096m was enough to work around this
    # locally, but we still had native crashes in CI towards the end of the run. No
    # reports yet of this affecting any users, so it's probably just because we're
    # reusing the daemon to build many different projects, and exposing a leak
    # somewhere. So set a limit to the number of times we reuse it.
    MAX_RUNS_PER_DAEMON = 100
    runs_per_daemon = 0

    def __init__(self, test, *layers, run=True, **kwargs):
        self.test = test
        if os.path.exists(test.run_dir):
            rmtree(test.run_dir)

        # Keep each test independent by clearing the pip cache. The appdirs module used in
        # pip._internal.locations is an old or modified version imported from
        # pip._internal.utils, which is why pip doesn't need to pass `appauthor`.
        cache_dir = appdirs.user_cache_dir("chaquopy/pip", appauthor=False)
        if exists(cache_dir):
            rmtree(cache_dir)

        self.project_dir = join(test.run_dir, "project")
        os.makedirs(self.project_dir)
        self.apply_layers(*layers)
        if run:
            self.rerun(**kwargs)

    def apply_layers(self, *layers):
        for layer in layers:
            # Most tests use the old Groovy DSL. Since the old DSL is implemented in
            # terms of the new DSL, this allows us to test both of them at once.
            if layer == "base":
                layer = "base/groovy"

            # "groovy" or "kotlin" here refers to the app/build.gradle file. The
            # language of the root build.gradle and settings.gradle files is determined
            # by agp_version.
            if layer in ["base/groovy", "base/kotlin"]:
                self.apply_layers("base/common", f"base/{agp_version}")

            # We use dir_util.copy_tree, because shutil.copytree can't merge into a
            # destination that already exists.
            dir_util._path_created.clear()  # https://bugs.python.org/issue10948
            dir_util.copy_tree(
                join(data_dir, layer), self.project_dir,
                preserve_times=False)  # https://github.com/gradle/gradle/issues/2301

    def rerun(self, *layers, succeed=True, variants=["debug"], env=None, add_path=None,
              **kwargs):
        if RunGradle.runs_per_daemon >= RunGradle.MAX_RUNS_PER_DAEMON:
            run([self.gradlew_path, "--stop"], cwd=self.project_dir, check=True)
            RunGradle.runs_per_daemon = 0
        RunGradle.runs_per_daemon += 1

        self.apply_layers(*layers)

        # In Android Studio Bumblebee and later, the new project wizard sets all plugin
        # versions using the `plugins` block of the top-level build.gradle file. This has a
        # strict syntax, and gradle.properties is the only way to pass variables into it.
        #
        # We also pass the repository location in the same way, in order to make it easy to
        # test a released version of Chaquopy by editing the following lines.
        gradle_props = f"{self.project_dir}/gradle.properties"
        set_property(gradle_props, "chaquopyRepository", f"{repo_root}/maven")
        set_property(gradle_props, "chaquopyVersion", chaquopy_version)
        java_version = get_property(gradle_props, "chaquopy.java.version")

        env = {} if env is None else env.copy()
        if add_path:
            add_path = [join(self.project_dir, path) for path in add_path]
            if os.name == "nt":
                # Gradle runs subprocesses using Java's ProcessBuilder, which on Windows uses
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

        status, self.stdout, self.stderr = self.run_gradle(variants, env, java_version)
        if status == 0:
            if not succeed:
                self.dump_run("run unexpectedly succeeded")

            for variant in variants:
                merged_kwargs = kwargs.copy()
                merged_kwargs.setdefault("abis", ["x86"])
                merged_kwargs.setdefault("python_version", DEFAULT_PYTHON_VERSION)
                if isinstance(variants, dict):
                    merged_kwargs.update(variants[variant])
                merged_kwargs = KwargsWrapper(merged_kwargs)
                try:
                    self.check_apk(variant, merged_kwargs)
                except Exception:
                    self.dump_run(f"check_apk failed for variant '{variant}'")
                self.test.assertFalse(merged_kwargs.unused_kwargs)

            # Run a second time to check all tasks are considered up to date.
            first_stdout = self.stdout
            status, second_stdout, second_stderr = \
                self.run_gradle(variants, env, java_version)
            if status != 0:
                self.stdout, self.stderr = second_stdout, second_stderr
                self.dump_run("Second run: exit status {}".format(status))

            # I've occasionally seen Gradle print a task header twice: once without
            # “UP-TO-DATE” and once with, even though the task was not re-run. So simply
            # searching the second run output for "Python" tasks is not reliable.
            num_tasks = 0
            for line in first_stdout.splitlines():
                if match := re.search(r"^> Task (\S+Python\S+)", line):
                    self.test.assertInLong(f"> Task {match[1]} UP-TO-DATE", second_stdout,
                                           msg=("=== FIRST RUN ===\n" + first_stdout))
                    num_tasks += 1
            self.test.assertGreater(num_tasks, 0, msg=first_stdout)

        else:
            if succeed:
                self.dump_run("exit status {}".format(status))

    def run_gradle(self, variants, env, java_version):
        # `--info` explains why tasks were not considered up to date.
        # `--console plain` prevents "String index out of range: -1" error on Windows.
        gradlew_flags = ["--stacktrace", "--info", "--console", "plain"]
        if env:
            # On macOS, the Gradle client doesn't update the environment of a running
            # daemon (https://github.com/gradle/gradle/issues/12905). On the other
            # platforms, this only affects specific variables such as PATH and TZ
            # (https://github.com/gradle/gradle/issues/10483).
            #
            # TODO: avoid this by changing as many tests as possible to use
            # gradle.properties instead.
            gradlew_flags.append("--no-daemon")

        # The following environment variables aren't affected by the above issue, either
        # because they never change, or because they aren't passed to the daemon.
        merged_env = {
            **os.environ,
            **env,
            "integration_dir": integration_dir,
            "JAVA_HOME": product_props[f"chaquopy.java.home.{java_version}"],
        }

        process = run([self.gradlew_path] + gradlew_flags +
                      [task_name("assemble", v) for v in variants],
                      cwd=self.project_dir,  # See Windows notes for add_path above.
                      capture_output=True, text=True, env=merged_env, timeout=600)
        return process.returncode, process.stdout, process.stderr

    @property
    def gradlew_path(self):
        return join(self.project_dir,
                    "gradlew.bat" if (os.name == "nt") else "gradlew")

    def check_apk(self, variant, kwargs):
        apk_zip, apk_dir = self.get_output("app", variant, "apk")
        self.test.pre_check(self, apk_dir, kwargs)

        # All AssetFinder ZIPs should be stored uncompressed (see comment in Common.assetZip).
        for info in apk_zip.infolist():
            with self.test.subTest(filename=info.filename):
                if info.filename.endswith(".imy"):
                    self.test.assertEqual(ZIP_STORED, info.compress_type)

                # Make sure we generate no empty files, as they may be unreadable on API levels
                # 23-28 if they happen to fall on a 4K boundary
                # (https://github.com/Electron-Cash/Electron-Cash/issues/2136).
                self.test.assertGreater(info.compress_size, 0)
                self.test.assertGreater(info.file_size, 0)

        self.check_assets(apk_dir, kwargs)
        self.check_lib(f"{apk_dir}/lib", kwargs)

        classes = kwargs.get("classes", {})
        self.test.update_classes(classes, chaquopy_classes())
        self.test.check_classes(classes, dex_classes(apk_dir))

        self.test.post_check(self, apk_dir, kwargs)

    def get_output(self, module, variant, ext):
        output_dir = join(self.project_dir, f"{module}/build/outputs/{ext}")
        if ext == "apk":
            *flavors, build_type = variant.split("-")
            if flavors:
                output_dir = join(
                    output_dir,
                    "".join(flavor if i == 0 else cap_first(flavor)
                            for i, flavor in enumerate(flavors))
                )
            output_dir = join(output_dir, build_type)
        zip_file = ZipFile(f"{output_dir}/{module}-{variant}.{ext}")

        zip_dir = join(self.test.run_dir, ext, variant)
        if exists(zip_dir):
            rmtree(zip_dir)
        zip_file.extractall(zip_dir)
        return zip_file, zip_dir

    def check_assets(self, apk_dir, kwargs):
        # Top-level assets
        asset_dir = join(apk_dir, "assets/chaquopy")
        python_version = kwargs["python_version"]
        abis = kwargs["abis"]
        abi_suffixes = ["common"] + abis
        self.test.assertCountEqual(
            ["app.imy", "bootstrap-native", "bootstrap.imy", "build.json", "cacert.pem"]
            + [f"{stem}-{suffix}.imy" for stem in ["requirements", "stdlib"]
               for suffix in abi_suffixes],
            os.listdir(asset_dir))

        # Python source
        pyc = kwargs.get("pyc", ["src", "pip", "stdlib"])
        extract_packages = kwargs.get("extract_packages", [])
        self.test.checkZip(f"{asset_dir}/app.imy", kwargs.get("app", []),
                           pyc=("src" in pyc), extract_packages=extract_packages)

        # Python requirements
        requirements = kwargs.get("requirements", [])
        for suffix in abi_suffixes:
            self.test.checkZip(
                f"{asset_dir}/requirements-{suffix}.imy",
                (requirements[suffix] if isinstance(requirements, dict)
                    else requirements if suffix == "common"
                    else []),
                pyc=("pip" in pyc), extract_packages=extract_packages,
                include_dist_info=kwargs.get("include_dist_info", False),
                dist_versions=(kwargs.get("dist_versions") if suffix == "common"
                               else None))

        # Python bootstrap
        with ZipFile(join(asset_dir, "bootstrap.imy")) as bootstrap_zip:
            self.check_pyc(bootstrap_zip, "java/__init__.pyc", kwargs)

        python_version_info = tuple(int(x) for x in python_version.split("."))
        stdlib_bootstrap_expected = {
            # This is the list from our minimum Python version. For why each of these
            # modules is needed, see BOOTSTRAP_NATIVE_STDLIB in PythonTasks.kt.
            "java", "_bz2.so", "_ctypes.so", "_datetime.so", "_lzma.so", "_random.so",
            "_sha512.so", "_struct.so", "binascii.so", "math.so", "mmap.so", "zlib.so",
        }
        if python_version_info >= (3, 12):
            stdlib_bootstrap_expected -= {"_sha512.so"}
            stdlib_bootstrap_expected |= {"_sha2.so"}

        bootstrap_native_dir = join(asset_dir, "bootstrap-native")
        self.test.assertCountEqual(abis, os.listdir(bootstrap_native_dir))
        for abi in abis:
            abi_dir = join(bootstrap_native_dir, abi)
            self.test.assertCountEqual(stdlib_bootstrap_expected, os.listdir(abi_dir))
            self.check_python_so(join(abi_dir, "_ctypes.so"), python_version, abi)

            java_dir = join(abi_dir, "java")
            self.test.assertCountEqual(["chaquopy.so"], os.listdir(java_dir))
            self.check_python_so(join(java_dir, "chaquopy.so"), python_version, abi)

        # Python stdlib
        with ZipFile(join(asset_dir, "stdlib-common.imy")) as stdlib_zip:
            stdlib_files = set(stdlib_zip.namelist())
            self.test.assertEqual("stdlib" in pyc, "argparse.pyc" in stdlib_files)
            self.test.assertNotEqual("stdlib" in pyc, "argparse.py" in stdlib_files)
            if "stdlib" in pyc:
                self.check_pyc(stdlib_zip, "argparse.pyc", kwargs)

        # Data files packaged with stdlib: see target/package_target.sh.
        for grammar_stem in ["Grammar", "PatternGrammar"]:
            self.test.assertIn("lib2to3/{}{}.final.0.pickle".format(
                                   grammar_stem, PYTHON_VERSIONS[python_version]),
                               stdlib_files)

        stdlib_native_expected = {
            # This is the list from the minimum supported Python version.
            "_asyncio.so", "_bisect.so", "_blake2.so", "_codecs_cn.so",
            "_codecs_hk.so", "_codecs_iso2022.so", "_codecs_jp.so", "_codecs_kr.so",
            "_codecs_tw.so", "_contextvars.so", "_csv.so", "_decimal.so", "_elementtree.so",
            "_hashlib.so", "_heapq.so", "_json.so", "_lsprof.so", "_md5.so",
            "_multibytecodec.so", "_multiprocessing.so", "_opcode.so", "_pickle.so",
            "_posixsubprocess.so", "_queue.so", "_sha1.so", "_sha256.so",
            "_sha3.so", "_socket.so", "_sqlite3.so", "_ssl.so",
            "_statistics.so", "_xxsubinterpreters.so", "_xxtestfuzz.so", "array.so",
            "audioop.so", "cmath.so", "fcntl.so", "ossaudiodev.so", "parser.so",
            "pyexpat.so", "resource.so", "select.so", "syslog.so", "termios.so",
            "unicodedata.so", "xxlimited.so"}
        if python_version_info >= (3, 9):
            stdlib_native_expected |= {"_zoneinfo.so"}
        if python_version_info >= (3, 10):
            stdlib_native_expected -= {"parser.so"}
            stdlib_native_expected |= {"xxlimited_35.so"}
        if python_version_info >= (3, 11):
            stdlib_native_expected |= {"_typing.so"}
        if python_version_info >= (3, 12):
            stdlib_native_expected -= {"_sha256.so", "_typing.so"}
            stdlib_native_expected |= {"_xxinterpchannels.so", "xxsubtype.so"}

        for abi in abis:
            stdlib_native_zip = ZipFile(join(asset_dir, f"stdlib-{abi}.imy"))
            self.test.assertEqual(stdlib_native_expected,
                                  set(stdlib_native_zip.namelist()))
            with TemporaryDirectory() as tmp_dir:
                test_module = "_asyncio.so"
                stdlib_native_zip.extract(test_module, tmp_dir)
                self.check_python_so(join(tmp_dir, test_module), python_version, abi)

        # build.json
        with open(join(asset_dir, "build.json")) as build_json_file:
            build_json = json.load(build_json_file)
        self.test.assertCountEqual(["python_version", "assets", "extract_packages"],
                                   build_json)
        self.test.assertEqual(python_version, build_json["python_version"])
        self.test.assertCountEqual(extract_packages, build_json["extract_packages"])
        asset_list = []
        for dirpath, dirnames, filenames in os.walk(asset_dir):
            asset_list += [relpath(join(dirpath, f), asset_dir).replace("\\", "/")
                           for f in filenames]
        self.test.assertEqual(
            {filename: file_sha1(join(asset_dir, filename))
             for filename in asset_list if filename != "build.json"},
            build_json["assets"])

    def check_pyc(self, zip_file, pyc_filename, kwargs):
        # See the list in importlib/_bootstrap_external.py.
        MAGIC = {
            "3.7": 3394,
            "3.8": 3413,
            "3.9": 3425,
            "3.10": 3439,
            "3.11": 3495,
            "3.12": 3531,
        }
        with zip_file.open(pyc_filename) as pyc_file:
            self.test.assertEqual(
                MAGIC[kwargs["python_version"]].to_bytes(2, "little") + b"\r\n",
                pyc_file.read(4))

    def check_lib(self, lib_dir, kwargs):
        python_version = kwargs["python_version"]
        abis = kwargs["abis"]
        self.test.assertCountEqual(abis, os.listdir(lib_dir))
        for abi in abis:
            abi_dir = join(lib_dir, abi)
            self.test.assertCountEqual(
                ["libchaquopy_java.so", "libcrypto_chaquopy.so",
                 f"libpython{kwargs['python_version']}.so", "libssl_chaquopy.so",
                 "libsqlite3_chaquopy.so"],
                os.listdir(abi_dir))
            self.check_python_so(join(abi_dir, "libchaquopy_java.so"), python_version, abi)

    def check_python_so(self, so_filename, python_version, abi):
        libpythons = []
        with open(so_filename, "rb") as so_file:
            ef = ELFFile(so_file)
            self.test.assertEqual(
                ef.header.e_machine,
                {"arm64-v8a": "EM_AARCH64",
                 "armeabi-v7a": "EM_ARM",
                 "x86": "EM_386",
                 "x86_64": "EM_X86_64"}[abi])

            for tag in ef.get_section_by_name(".dynamic").iter_tags():
                if tag.entry.d_tag == "DT_NEEDED" and \
                   tag.needed.startswith("libpython"):
                    libpythons.append(tag.needed)
        self.test.assertEqual([f"libpython{python_version}.so"], libpythons)

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
    build_tools_dir = join(os.environ["ANDROID_HOME"], "build-tools")
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
    # Don't include the :app: prefix: the project may have multiple modules (e.g.
    # dynamic features or AARs).
    return (prefix +
            "".join(cap_first(word) for word in variant.split("-")) +
            cap_first(suffix))


# Differs from str.capitalize() because it only affects the first character
def cap_first(s):
    return s if (s == "") else (s[0].upper() + s[1:])


NO_DEFAULT = object()

def get_property(filename, key, default=NO_DEFAULT):
    with open(filename) as props_file:
        props = PropertiesFile.load(props_file)
        return props[key] if (default is NO_DEFAULT) else props.get(key, default)


def set_property(filename, key, value):
    try:
        with open(filename) as props_file:
            props = PropertiesFile.load(props_file)
    except FileNotFoundError:
        props = PropertiesFile()

    if value is None:
        props.pop(key, None)
    else:
        props[key] = value
    with open(filename, "w") as props_file:
        props.dump(props_file)


# On Windows, rmtree often gets blocked by the virus scanner. See comment in our copy of
# pip/_internal/utils/misc.py.
def rmtree(path):
    if os.name == "nt":  # https://bugs.python.org/issue18199
        path = "\\\\?\\" + path.replace("/", "\\")
    shutil.rmtree(path, onerror=rmtree_errorhandler)

@retry(wait_fixed=50, stop_max_delay=3000)
def rmtree_errorhandler(func, path, exc_info):
    func(path)  # Use the original function to repeat the operation.
