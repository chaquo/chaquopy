from __future__ import absolute_import, division, print_function

from distutils.dir_util import copy_tree
from kwonly_args import kwonly_defaults, KWONLY_REQUIRED
import os
from os.path import abspath, dirname, join
import shutil
import subprocess
from unittest import TestCase
from zipfile import ZipFile


class GradleTestCase(TestCase):
    @kwonly_defaults
    def check_apk(self, run, variant="debug", abis=KWONLY_REQUIRED):
        apk_subdir = join(run.apk, variant)
        for filename in ["chaquopy.zip", "stdlib.zip"]:
            self.assertIsFile(join(apk_subdir, "assets/chaquopy", filename))

        self.assertEqual(set(abis),
                         set(os.listdir(join(apk_subdir, "assets/chaquopy/lib-dynload"))))
        for abi in abis:
            # The native module list here is intended to be representative, not complete.
            for filename in ["_ctypes.so", "select.so", "unicodedata.so",
                             "java/__init__.py", "java/chaquopy.so"]:
                self.assertIsFile(join(apk_subdir, "assets/chaquopy/lib-dynload", abi, filename))

        self.assertEqual(set(abis), set(os.listdir(join(apk_subdir, "lib"))))
        for abi in abis:
            for filename in ["libchaquopy_java.so", "libcrystax.so", "libpython2.7.so"]:
                self.assertIsFile(join(apk_subdir, "lib", abi, filename))

        dex = open(join(apk_subdir, "classes.dex"), "rb").read()
        for s in [b"com/chaquo/python/Python", b"Python already started"]:
            self.assertIn(s, dex)

    def assertIsFile(self, filename):
        self.assertTrue(os.path.isfile(filename), filename)

    # Prints b as a multi-line string rather than a repr().
    def assertInLong(self, a, b):
        try:
            TestCase.assertIn(self, a, b)
        except AssertionError:
            raise AssertionError("'{}' not found in:\n{}".format(a, b))


class Basic(GradleTestCase):
    def test_base(self):
        run = RunGradle("base")
        self.check_apk(run, abis=["armeabi-v7a", "x86"])

        run.rerun()  # TODO #5204 extra run required
        run.rerun()
        self.assertInLong(":app:generatePythonDebugAssets UP-TO-DATE", run.stdout)
        self.assertInLong(":app:generatePythonDebugJniLibs UP-TO-DATE", run.stdout)

    def test_variant(self):
        variants = ["red-debug", "blue-debug"]
        run = RunGradle("base", "variant", variants=variants)
        for variant in variants:
            self.check_apk(run, variant=variant, abis=["armeabi-v7a", "x86"])


class AndroidPlugin(GradleTestCase):
    def test_misordered(self):
        run = RunGradle("base", "android_plugin_misordered", succeed=False)
        self.assertInLong("project.android not set", run.stderr)

    def test_old(self):
        run = RunGradle("base", "android_plugin_old", succeed=False)
        self.assertInLong("requires Android Gradle plugin version 2.3.0", run.stderr)

    # This test may have to be temporarily disabled if there are no released versions it applies to.
    def test_untested(self):
        run = RunGradle("base", "android_plugin_untested")
        self.assertInLong("not been tested with Android Gradle plugin versions beyond 2.3.0",
                          run.stdout)

    def test_new(self):
        run = RunGradle("base", "android_plugin_new", succeed=False)
        self.assertInLong("does not work with Android Gradle plugin version 3.0.0", run.stderr)


class PythonVersion(GradleTestCase):
    def test_missing(self):
        run = RunGradle("base", "python_version_missing", succeed=False)
        self.assertInLong("python.version not set", run.stderr)

    def test_invalid(self):
        run = RunGradle("base", "python_version_invalid", succeed=False)
        self.assertInLong("Python version '2.7.99'. Available versions are [2.7.10]",
                          run.stderr)

    # TODO #5202
    def test_variant(self):
        run = RunGradle("base", "python_version_variant", succeed=False)
        self.assertInLong("Could not find method python", run.stderr)


class AbiFilters(GradleTestCase):
    def test_missing(self):
        run = RunGradle("base", "abi_filters_missing", succeed=False)
        self.assertInLong("ndk.abiFilters not set", run.stderr)

    def test_invalid(self):
        run = RunGradle("base", "abi_filters_invalid", succeed=False)
        self.assertInLong("ABI 'armeabi'. Supported ABIs are [armeabi-v7a, x86].", run.stderr)

    # TODO #5202
    def test_variant(self):
        run = RunGradle("base", "abi_filters_variant", succeed=False)
        self.assertInLong("not yet support per-flavor abiFilters", run.stderr)

    # Testing adding an ABI, because when removing one I kept getting this error: Execution
    # failed for task ':app:transformNativeLibsWithStripDebugSymbolForDebug'.
    # java.io.IOException: Failed to delete
    # ....\app\build\intermediates\transforms\stripDebugSymbol\release\folders\2000\1f\main\lib\armeabi-v7a
    # I've reported https://issuetracker.google.com/issues/62291921. Other people have had
    # similar problems, e.g. https://github.com/mrmaffen/vlc-android-sdk/issues/63.
    def test_change(self):
        run = RunGradle("base", "abi_filters_single")
        self.check_apk(run, abis=["x86"])
        run.rerun()  # TODO #5204 extra run required
        run.apply_layer("base")
        run.rerun()
        self.check_apk(run, abis=["armeabi-v7a", "x86"])


data_dir  = abspath(join(dirname(__file__), "data"))
repo_root = abspath(join(dirname(__file__), "../../../../.."))
build_dir = abspath(join(repo_root, "product/gradle-plugin/build/integrationTest"))
demo_dir = abspath(join(repo_root, "demo"))


class RunGradle(object):
    @kwonly_defaults
    def __init__(self, succeed=True, variants=["debug"], *data_layers):
        self.run_dir = join(build_dir, "+".join(data_layers))
        if os.path.exists(self.run_dir):
            shutil.rmtree(self.run_dir)

        self.project_dir = join(self.run_dir, "project")
        os.makedirs(self.project_dir)
        shutil.copy(join(demo_dir, "local.properties"), self.project_dir)
        for layer in data_layers:
            self.apply_layer(layer)

        self.succeed = succeed
        self.rerun(variants=variants)

    def apply_layer(self, layer):
        copy_tree(join(data_dir, layer), self.project_dir)

    @kwonly_defaults
    def rerun(self, variants=["debug"]):
        os.chdir(self.project_dir)
        # TODO #5184 Windows-specific
        process = subprocess.Popen(["gradlew.bat"] +
                                   [(":app:assemble" + variant_task_name(v)) for v in variants],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.stdout, self.stderr = process.communicate()
        if process.wait() == 0:
            if not self.succeed:
                dump_run(self, "run unexpectedly succeeded")
            # TODO #5180 Android plugin version 3 adds an extra variant directory below "apk".
            for variant in variants:
                apk_file = join(self.project_dir, "app/build/outputs/apk/app-{}.apk".format(variant))
                self.apk = join(self.run_dir, "apk")
                apk_subdir = join(self.apk, variant)
                if os.path.exists(apk_subdir):
                    shutil.rmtree(apk_subdir)
                os.makedirs(apk_subdir)
                ZipFile(apk_file).extractall(apk_subdir)
        else:
            if self.succeed:
                dump_run(self, "run failed")


def variant_task_name(variant):
    return "".join(word.capitalize() for word in variant.split("-"))


def dump_run(run, msg):
    raise AssertionError(msg + "\n" +
                         "=== STDOUT ===\n" + run.stdout +
                         "=== STDERR ===\n" + run.stderr)


del GradleTestCase
