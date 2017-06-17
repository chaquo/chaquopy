from __future__ import absolute_import, division, print_function

from distutils.dir_util import copy_tree
import distutils.util
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
        self.RunGradle("base", "Basic/variant", variants=variants)


class AndroidPlugin(GradleTestCase):
    def test_misordered(self):
        run = self.RunGradle("base", "AndroidPlugin/misordered", succeed=False)
        self.assertInLong("project.android not set", run.stderr)

    def test_old(self):
        run = self.RunGradle("base", "AndroidPlugin/old", succeed=False)
        self.assertInLong("requires Android Gradle plugin version 2.3.0", run.stderr)

    @skip("no applicable versions currently exist")
    def test_untested(self):
        run = self.RunGradle("base", "AndroidPlugin/untested")
        self.assertInLong("not been tested with Android Gradle plugin versions beyond 2.3.3",
                          run.stdout)

    def test_new(self):
        run = self.RunGradle("base", "AndroidPlugin/new", succeed=False)
        self.assertInLong("does not work with Android Gradle plugin version 3.0.0", run.stderr)


class ApiLevel(GradleTestCase):
    def test_old(self):
        run = self.RunGradle("base", "ApiLevel/9")
        run.apply_layers("ApiLevel/8")
        run.rerun(succeed=False)
        self.assertInLong("debug: Chaquopy requires minSdkVersion 9 or higher", run.stderr)

    def test_variant(self):
        run = self.RunGradle("base", "ApiLevel/variant", succeed=False)
        self.assertInLong("redDebug: Chaquopy requires minSdkVersion 9 or higher", run.stderr)


class PythonVersion(GradleTestCase):
    def test_missing(self):
        run = self.RunGradle("base", "PythonVersion/missing", succeed=False)
        self.assertInLong("debug: python.version not set", run.stderr)

    def test_invalid(self):
        run = self.RunGradle("base", "PythonVersion/invalid", succeed=False)
        self.assertInLong("debug: invalid Python version '2.7.99'. Available versions are [2.7.10]",
                          run.stderr)

    # TODO #5202
    def test_variant(self):
        run = self.RunGradle("base", "PythonVersion/variant", succeed=False)
        self.assertInLong("Could not find method python", run.stderr)


class AbiFilters(GradleTestCase):
    def test_missing(self):
        run = self.RunGradle("base", "AbiFilters/missing", succeed=False)
        self.assertInLong("debug: Chaquopy requires ndk.abiFilters", run.stderr)

    def test_invalid(self):
        run = self.RunGradle("base", "AbiFilters/invalid", succeed=False)
        self.assertInLong("debug: Chaquopy does not support the ABI 'armeabi'. "
                          "Supported ABIs are [armeabi-v7a, x86].", run.stderr)

    # TODO #5202
    def test_variant(self):
        run = self.RunGradle("base", "AbiFilters/variant", succeed=False)
        self.assertInLong("redDebug: Chaquopy does not support per-flavor abiFilters", run.stderr)

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
    # Missing python src directory is already tested by Basic.

    def test_change(self):
        run = self.RunGradle("base", "PythonSrc/empty")

        run.apply_layers("PythonSrc/1")                                 # Add
        run.rerun()
        run.apply_layers("PythonSrc/2")                                 # Modify
        run.rerun()
        os.remove(join(run.project_dir, "app/src/main/python/one.py"))  # Remove
        run.rerun()


class PythonReqs(GradleTestCase):
    def test_build_python(self):
        run = self.RunGradle("base", "PythonReqs/build_python_3", requirements=["apple"])

        run.apply_layers("PythonReqs/build_python_invalid")
        run.rerun(succeed=False)
        self.assertInLong("problem occurred starting process 'command 'pythoninvalid''", run.stderr)

    def test_change(self):
        run = self.RunGradle("base")                               # No reqs
        run.apply_layers("PythonReqs/1a")                          # Add one req
        run.rerun(requirements=["apple"])
        run.apply_layers("PythonReqs/1")                           # Modify to a req with its own dependency
        run.rerun(requirements=["alpha", "alpha_dep"])
        run.apply_layers("PythonReqs/2")                           # Add another req
        run.rerun(requirements=["alpha", "alpha_dep", "bravo"])
        run.apply_layers("base")                                   # Remove all
        run.rerun()

    def test_reqs_file(self):
        self.RunGradle("base", "PythonReqs/reqs_file", requirements=["apple", "bravo"])

    def test_wheel_file(self):
        self.RunGradle("base", "PythonReqs/wheel_file", requirements=["alpha_dep"])

    def test_sdist_file(self):
        run = self.RunGradle("base", "PythonReqs/sdist_file", succeed=False)
        self.assertInLong("alpha_dep-0.0.1.tar.gz: Chaquopy does not support sdist packages", run.stderr)

    def test_editable(self):
        run = self.RunGradle("base", "PythonReqs/editable", succeed=False)
        self.assertInLong("src: Chaquopy does not support editable requirements", run.stderr)

    def test_wheel_index(self):
        # packages/dist should contain a wheel for each platform the tests may be run on. All
        # the test platform wheels have version 0.2, while the Android wheels have version 0.1.
        # This tests that pip always uses the target platform and ignores the workstation
        # platform.
        self.assertIn(distutils.util.get_platform(), ["mingw"])

        run = self.RunGradle("base", "PythonReqs/wheel_index_1",   # Has Android wheel
                             requirements=["native1_android_todo"])

        run.apply_layers("PythonReqs/wheel_index_2")               # No Android wheel
        run.rerun(succeed=False)
        self.assertInLong("No matching distribution found for native2", run.stderr)

    def test_sdist_index(self):
        # Similarly to test_wheel_index, this test has an sdist for version 0.2 and a wheel for
        # version 0.1.
        run = self.RunGradle("base", "PythonReqs/sdist_index_1",
                             requirements=["sdist1_android_todo"])

        # While this test has only an sdist.
        run.apply_layers("PythonReqs/sdist_index_2")
        run.rerun(succeed=False)
        self.assertInLong("No matching distribution found for sdist2 "
                          "(NOTE: Chaquopy only supports wheels, not sdist packages)", run.stderr)


class License(GradleTestCase):
    def test_empty_key(self):
        run = self.RunGradle("base", key="", succeed=False)
        self.assertInLong("Chaquopy license verification failed", run.stderr)

        run.apply_layers("License/demo")
        run.rerun(licensed=True)

        run.apply_key(None)
        run.rerun(licensed=False)

    def test_key(self):
        run = self.RunGradle("base", key="invalid", succeed=False)
        self.assertInLong("Chaquopy license verification failed", run.stderr)

        run.apply_key("AU5-6D8smj5fE6b53i9P7czOLV1L4Gf8W1L6RB_qkOQr")
        run.rerun(licensed=True)

        run.apply_key(None)
        run.rerun(licensed=False)


data_dir  = abspath(join(dirname(__file__), "data"))
repo_root = abspath(join(dirname(__file__), "../../../../.."))
build_dir = abspath(join(repo_root, "product/gradle-plugin/build/test/integration"))
demo_dir = abspath(join(repo_root, "demo"))


class RunGradle(object):
    @kwonly_defaults
    def __init__(self, test, key=None, *layers,**kwargs):
        self.test = test

        module, cls, func = test.id().split(".")
        self.run_dir = join(build_dir, cls, func)
        if os.path.exists(self.run_dir):
            rmtree(self.run_dir)

        self.project_dir = join(self.run_dir, "project")
        os.makedirs(self.project_dir)
        self.apply_layers(*layers)
        self.apply_key(key)

        self.rerun(**kwargs)

    def apply_layers(self, *layers):
        for layer in layers:
            copy_tree(join(data_dir, layer), self.project_dir,
                      preserve_times=False)  # https://github.com/gradle/gradle/issues/2301

    def apply_key(self, key):
        LP_FILENAME = "local.properties"
        shutil.copy(join(demo_dir, LP_FILENAME), self.project_dir)
        if key is not None:
            with open(join(self.project_dir, LP_FILENAME), "a") as lp_file:
                print("chaquopy.license=" + key, file=lp_file)

    @kwonly_defaults
    def rerun(self, succeed=True, variants=["debug"], **kwargs):
        status, self.stdout, self.stderr = self.run_gradle(variants)

        if status == 0:
            if not succeed:
                self.dump_run("run unexpectedly succeeded")

            # TODO #5180 Android plugin version 3 adds an extra variant directory below "apk".
            for variant in variants:
                apk_file = join(self.project_dir, "app/build/outputs/apk/app-{}.apk".format(variant))
                apk_dir = join(self.run_dir, "apk", variant)
                if os.path.exists(apk_dir):
                    rmtree(apk_dir)
                os.makedirs(apk_dir)
                ZipFile(apk_file).extractall(apk_dir)
                self.check_apk(apk_dir, **kwargs)

            # Run a second time to check all tasks are considered up to date.
            status, self.stdout, self.stderr = self.run_gradle(variants)
            if status != 0:
                self.dump_run("exit status {}".format(status))
            self.tedst.assertInLong(":app:extractPythonBuildPackages UP-TO-DATE", self.stdout)
            for variant in variants:
                for suffix in ["Requirements", "Ticket", "Assets", "JniLibs"]:
                    msg = task_name(":app:generate", variant, "Python" + suffix) + " UP-TO-DATE"
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
                                   [task_name(":app:assemble", v) for v in variants],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return process.wait(), stdout, stderr

    @kwonly_defaults
    def check_apk(self, apk_dir, abis=["x86"], requirements=[], licensed=False):
        asset_dir = join(apk_dir, "assets/chaquopy")

        app_zip = ZipFile(join(asset_dir, "app.zip"))
        app_check_base_name = join(self.run_dir, "app-check")
        # If app/src/main/python didn't already exist, the plugin should have created it.
        shutil.make_archive(app_check_base_name, "zip",
                            join(self.project_dir, "app/src/main/python"))
        app_check_zip = ZipFile(app_check_base_name + ".zip")
        self.test.assertEqual(set(app_zip.namelist()), set(app_check_zip.namelist()))
        for name in app_zip.namelist():
            self.test.assertEqual(app_zip.getinfo(name).CRC, app_check_zip.getinfo(name).CRC, name)

        reqs_zip = ZipFile(join(asset_dir, "requirements.zip"))
        reqs_toplevel = set([path.partition("/")[0] for path in reqs_zip.namelist()
                             if ".dist-info" not in path])
        self.test.assertEqual(set(requirements), reqs_toplevel)

        # Python stdlib
        self.test.assertIsFile(join(asset_dir, "stdlib.zip"))
        self.test.assertEqual(set(abis),
                              set(os.listdir(join(asset_dir, "lib-dynload"))))
        for abi in abis:
            # The native module list here is intended to be representative, not complete.
            for filename in ["_ctypes.so", "select.so", "unicodedata.so",
                             "java/__init__.py", "java/chaquopy.so"]:
                self.test.assertIsFile(join(asset_dir, "lib-dynload", abi, filename))

        # JNI libs
        self.test.assertEqual(set(abis), set(os.listdir(join(apk_dir, "lib"))))
        for abi in abis:
            for filename in ["libchaquopy_java.so", "libcrystax.so", "libpython2.7.so"]:
                self.test.assertIsFile(join(apk_dir, "lib", abi, filename))

        # Chaquopy runtime library
        self.test.assertIsFile(join(asset_dir, "chaquopy.zip"))
        dex = open(join(apk_dir, "classes.dex"), "rb").read()
        for s in [b"com/chaquo/python/Python", b"Python already started"]:
            self.test.assertIn(s, dex)

        ticket_file_size = os.stat(join(asset_dir, "ticket.txt")).st_size
        if licensed:
            self.test.assertGreater(ticket_file_size, 0)
        else:
            self.test.assertEqual(ticket_file_size, 0)

    def dump_run(self, msg):
        self.test.fail(msg + "\n" +
                       "=== STDOUT ===\n" + self.stdout +
                       "=== STDERR ===\n" + self.stderr)


def task_name(prefix, variant, suffix=""):
    # Differs from str.capitalize() because it only affects the first character
    def cap_first(s):
        return s if (s == "") else (s[0].upper() + s[1:])

    return (prefix +
            "".join(cap_first(word) for word in variant.split("-")) +
            cap_first(suffix))


# shutil.rmtree is unreliable on Windows: it frequently fails with Windows error 145 (directory
# not empty), even though it has already removed everything from that directory.
def rmtree(path):
    subprocess.check_call(["rm", "-rf", path])


del GradleTestCase
