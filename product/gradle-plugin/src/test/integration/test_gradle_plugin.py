from __future__ import absolute_import, division, print_function

from distutils.dir_util import copy_tree
from kwonly_args import kwonly_defaults, KWONLY_REQUIRED
import os
from os.path import abspath, dirname, join
import shutil
import subprocess
import time
from unittest import skip, TestCase
from zipfile import ZipFile


class GradleTestCase(TestCase):
    def RunGradle(self, *args, **kwargs):
        return RunGradle(self, *args, **kwargs)

    def assertIsFile(self, filename):
        self.assertTrue(os.path.isfile(filename), filename)

    # Prints b as a multi-line string rather than a repr().
    def assertInLong(self, a, b, re=False):
        try:
            if re:
                self.assertRegexpMatches(b, a)
            else:
                self.assertIn(a, b)
        except AssertionError:
            raise AssertionError("'{}' not found in:\n{}".format(a, b))


class Basic(GradleTestCase):
    def test_base(self):
        self.RunGradle("base")

    def test_variant(self):
        variants = ["red-debug", "blue-debug"]
        self.RunGradle("base", "variant", variants=variants)


class AndroidPlugin(GradleTestCase):
    def test_misordered(self):
        run = self.RunGradle("base", "android_plugin_misordered", succeed=False)
        self.assertInLong("project.android not set", run.stderr)

    def test_old(self):
        run = self.RunGradle("base", "android_plugin_old", succeed=False)
        self.assertInLong("requires Android Gradle plugin version 2.3.0", run.stderr)

    @skip("no applicable versions currently exist")
    def test_untested(self):
        run = self.RunGradle("base", "android_plugin_untested")
        self.assertInLong("not been tested with Android Gradle plugin versions beyond 2.3.3",
                          run.stdout)

    def test_new(self):
        run = self.RunGradle("base", "android_plugin_new", succeed=False)
        self.assertInLong("does not work with Android Gradle plugin version 3.0.0", run.stderr)


class ApiLevel(GradleTestCase):
    def test_old(self):
        run = self.RunGradle("base", "api_level_9")
        run.apply_layers("api_level_8")
        run.rerun(succeed=False)
        self.assertInLong("debug: Chaquopy requires minSdkVersion 9 or higher", run.stderr)

    def test_variant(self):
        run = self.RunGradle("base", "api_level_variant", succeed=False)
        self.assertInLong("redDebug: Chaquopy requires minSdkVersion 9 or higher", run.stderr)


class PythonVersion(GradleTestCase):
    def test_missing(self):
        run = self.RunGradle("base", "python_version_missing", succeed=False)
        self.assertInLong("debug: python.version not set", run.stderr)

    def test_invalid(self):
        run = self.RunGradle("base", "python_version_invalid", succeed=False)
        self.assertInLong("debug: invalid Python version '2.7.99'. Available versions are [2.7.10]",
                          run.stderr)

    # TODO #5202
    def test_variant(self):
        run = self.RunGradle("base", "python_version_variant", succeed=False)
        self.assertInLong("Could not find method python", run.stderr)


class AbiFilters(GradleTestCase):
    def test_missing(self):
        run = self.RunGradle("base", "abi_filters_missing", succeed=False)
        self.assertInLong("debug: Chaquopy requires ndk.abiFilters", run.stderr)

    def test_invalid(self):
        run = self.RunGradle("base", "abi_filters_invalid", succeed=False)
        self.assertInLong("debug: Chaquopy does not support the ABI 'armeabi'. "
                          "Supported ABIs are [armeabi-v7a, x86].", run.stderr)

    # TODO #5202
    def test_variant(self):
        run = self.RunGradle("base", "abi_filters_variant", succeed=False)
        self.assertInLong("redDebug: Chaquopy does not support per-flavor abiFilters", run.stderr)

    # We only test adding an ABI, because when removing one I kept getting this error: Execution
    # failed for task ':app:transformNativeLibsWithStripDebugSymbolForDebug'.
    # java.io.IOException: Failed to delete
    # ....\app\build\intermediates\transforms\stripDebugSymbol\release\folders\2000\1f\main\lib\armeabi-v7a
    # I've reported https://issuetracker.google.com/issues/62291921. Other people have had
    # similar problems, e.g. https://github.com/mrmaffen/vlc-android-sdk/issues/63.
    def test_change(self):
        run = self.RunGradle("base")
        run.apply_layers("abi_filters_2")
        run.rerun(abis=["armeabi-v7a", "x86"])


class PythonSrc(GradleTestCase):
    # Missing python src directory is already tested by Basic.

    def test_change(self):
        run = self.RunGradle("base", "python_src_empty")

        # Add
        run.apply_layers("python_src_1")
        run.rerun()

        # Modify
        run.apply_layers("python_src_2")
        run.rerun()

        # Remove
        os.remove(join(run.project_dir, "app/src/main/python/one.py"))
        run.rerun()


class PythonDeps(GradleTestCase):
    pass
    # FIXME:
    # Add and remove, including removing all
    # target-packages.zip should have no .pyc files: also extend to app.zip
    # buildPython
    # -r with relative filename
    # Package selection using --no-index and (--find-links or --index-url /local/path)
    #   compatibility checks should use target environment
    #   egg
    #   wheel
    #   No sdist, even from explicit local filename
    #   No -e
    #   Give appropriate error if package existed but no compatible version found


data_dir  = abspath(join(dirname(__file__), "data"))
repo_root = abspath(join(dirname(__file__), "../../../../.."))
build_dir = abspath(join(repo_root, "product/gradle-plugin/build/test/integration"))
demo_dir = abspath(join(repo_root, "demo"))


class RunGradle(object):
    def __init__(self, test, *layers, **kwargs):
        self.test = test

        self.run_dir = join(build_dir, test.id().partition(".")[2])
        if os.path.exists(self.run_dir):
            rmtree(self.run_dir)

        self.project_dir = join(self.run_dir, "project")
        os.makedirs(self.project_dir)
        shutil.copy(join(demo_dir, "local.properties"), self.project_dir)
        self.apply_layers(*layers)

        self.rerun(**kwargs)

    def apply_layers(self, *layers):
        if hasattr(self, "stdout"):
            # In Gradle 3.3, if the content of the build script changes immediately after a
            # build, the daemon seems to cache the compiled old script under the new script's
            # hash, meaning it will reuse the compiled old script incorrectly when we try and
            # run the new script. We could work around that with --no-daemon
            # --recompile-scripts (https://github.com/gradle/gradle/issues/1425), but that
            # would be far slower. I've reported https://github.com/gradle/gradle/issues/2301.
            time.sleep(0.5)
        for layer in layers:
            copy_tree(join(data_dir, layer), self.project_dir, preserve_times=False)

    @kwonly_defaults
    def rerun(self, succeed=True, variants=["debug"], abis=["x86"]):
        status, self.stdout, self.stderr = self.run_gradle(variants)

        if status == 0:
            if not succeed:
                self.dump_run("run unexpectedly succeeded")

            # TODO #5180 Android plugin version 3 adds an extra variant directory below "apk".
            for variant in variants:
                apk_file = join(self.project_dir, "app/build/outputs/apk/app-{}.apk".format(variant))
                self.apk = join(self.run_dir, "apk")
                apk_subdir = join(self.apk, variant)
                if os.path.exists(apk_subdir):
                    rmtree(apk_subdir)
                os.makedirs(apk_subdir)
                ZipFile(apk_file).extractall(apk_subdir)
                self.check_apk(variant, abis)

            status, self.stdout, self.stderr = self.run_gradle(variants)
            if status != 0:
                self.dump_run("exit status {}".format(status))
            self.test.assertInLong(":app:extractPythonBuildPackages UP-TO-DATE", self.stdout)
            for variant in variants:
                for prefix, suffix in [("get", "pythonRequirements"), ("generate", "pythonAssets"),
                                       ("generate", "pythonJniLibs")]:
                    msg = variant_task_name(":app:" + prefix, variant, suffix) + " UP-TO-DATE"
                    self.test.assertInLong(msg, self.stdout)

        else:
            if succeed:
                self.dump_run("exit status {}".format(status))

    def run_gradle(self, variants):
        os.chdir(self.project_dir)
        # TODO #5184 Windows-specific
        # --info explains why tasks were not considered up to date.
        # --console plain prevents output being truncated by a "String index out of range: -1" error.
        process = subprocess.Popen(["gradlew.bat", "--stacktrace", "--info", "--console", "plain"] +
                                   [(variant_task_name(":app:assemble", v)) for v in variants],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return process.wait(), stdout, stderr

    def check_apk(self, variant, abis):
        apk_subdir = join(self.apk, variant)
        for filename in ["app.zip", "chaquopy.zip", "stdlib.zip"]:
            self.test.assertIsFile(join(apk_subdir, "assets/chaquopy", filename))

        app_check_base_name = join(self.run_dir, "app-check")
        # If app/src/main/python didn't already exist, the plugin should have created it.
        shutil.make_archive(app_check_base_name, "zip",
                            join(self.project_dir, "app/src/main/python"))
        app_check = ZipFile(app_check_base_name + ".zip")
        app = ZipFile(join(apk_subdir, "assets/chaquopy/app.zip"))
        self.test.assertEqual(sorted(app.namelist()), sorted(app_check.namelist()))
        for name in app.namelist():
            self.test.assertEqual(app.getinfo(name).CRC, app_check.getinfo(name).CRC, name)

        self.test.assertEqual(set(abis),
                              set(os.listdir(join(apk_subdir, "assets/chaquopy/lib-dynload"))))
        for abi in abis:
            # The native module list here is intended to be representative, not complete.
            for filename in ["_ctypes.so", "select.so", "unicodedata.so",
                             "java/__init__.py", "java/chaquopy.so"]:
                self.test.assertIsFile(join(apk_subdir, "assets/chaquopy/lib-dynload", abi, filename))

        self.test.assertEqual(set(abis), set(os.listdir(join(apk_subdir, "lib"))))
        for abi in abis:
            for filename in ["libchaquopy_java.so", "libcrystax.so", "libpython2.7.so"]:
                self.test.assertIsFile(join(apk_subdir, "lib", abi, filename))

        dex = open(join(apk_subdir, "classes.dex"), "rb").read()
        for s in [b"com/chaquo/python/Python", b"Python already started"]:
            self.test.assertIn(s, dex)

    def dump_run(self, msg):
        self.test.fail(msg + "\n" +
                       "=== STDOUT ===\n" + self.stdout +
                       "=== STDERR ===\n" + self.stderr)


def variant_task_name(prefix, variant, suffix=""):
    def cap(s):
        return s if (s == "") else (s[0].upper() + s[1:])

    return (prefix +
            "".join(cap(word) for word in variant.split("-")) +
            cap(suffix))


# shutil.rmtree is unreliable on Windows: it frequently fails with Windows error 145 (directory
# not empty), even though it has already removed everything from that directory.
def rmtree(path):
    subprocess.check_call(["rm", "-rf", path])


del GradleTestCase
