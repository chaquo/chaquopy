from __future__ import absolute_import, division, print_function

from distutils.dir_util import copy_tree
import distutils.util
from jproperties import Properties
from kwonly_args import kwonly_defaults
import os
from os.path import abspath, dirname, join
import re
import shutil
import subprocess
import sys
from unittest import skip, TestCase
from zipfile import ZipFile


class GradleTestCase(TestCase):
    longMessage = True

    def RunGradle(self, *args, **kwargs):
        return RunGradle(self, *args, **kwargs)

    def assertIsFile(self, filename):
        self.assertTrue(os.path.isfile(filename), filename)

    # Prints b as a multi-line string rather than a repr().
    def assertInLong(self, a, b, re=False, msg=None):
        try:
            if re:
                self.assertRegexpMatches(b, a)
            else:
                self.assertIn(a, b)
        except self.failureException:
            msg = self._formatMessage(msg, "'{}' not found in:\n{}".format(a, b))
            raise self.failureException(msg)

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
        self.assertInLong("requires Android Gradle plugin version 2.2.0", run.stderr)

    def test_untested(self):
        run = self.RunGradle("base", "AndroidPlugin/untested", succeed=None)
        self.assertInLong("not been tested with Android Gradle plugin versions beyond 3.0.0",
                          run.stdout)

    @skip("no incompatible new versions are currently known")
    def test_new(self):
        run = self.RunGradle("base", "AndroidPlugin/new", succeed=False)
        self.assertInLong("does not work with Android Gradle plugin version 9.9.9-alpha1",
                          run.stderr)


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
    # Missing src/main/python directory is already tested by Basic.

    def test_change(self):
        # Git can't track a directory hierarchy containing no files.
        empty_src = join(integration_dir, "data/PythonSrc/empty/app/src/main/python")
        if not os.path.isdir(empty_src):
            os.makedirs(empty_src)
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
        run.apply_layers("PythonReqs/1")                           # Replace with a req which has a
        run.rerun(requirements=["alpha", "alpha_dep"])             #   transitive dependency
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
        self.assertInLong("alpha_dep-0.0.1.tar.gz: Chaquopy does not support sdist packages",
                          run.stderr)

    def test_editable(self):
        run = self.RunGradle("base", "PythonReqs/editable", succeed=False)
        self.assertInLong("src: Chaquopy does not support editable requirements", run.stderr)

    def test_wheel_index(self):
        # All the workstation platform wheels have version 0.2, while the Android wheels have
        # version 0.1. This tests that pip always uses the target platform and ignores the
        # workstation platform.
        #
        # If testing on another platform, add it to the list below, and add a corresponding
        # wheel to packages/dist.
        self.assertIn(distutils.util.get_platform(), ["linux-x86_64", "mingw"])

        run = self.RunGradle("base", "PythonReqs/wheel_index_1",     # Has Android and workstation
                             requirements=["native1_android_todo"])  #   wheels

        run.apply_layers("PythonReqs/wheel_index_2")                 # Only has workstation wheels
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


class StaticProxy(GradleTestCase):
    def test_change(self):
        run = self.RunGradle("base", "StaticProxy/reqs", requirements=["static_proxy"],
                             static_proxies=["a.ReqsA1", "b.ReqsB1"])
        run.apply_layers("StaticProxy/src_1")       # Src should take priority over reqs.
        run.rerun(requirements=["static_proxy"], static_proxies=["a.SrcA1", "b.ReqsB1"])
        run.apply_layers("StaticProxy/src_only")    # Remove reqs
        run.rerun(static_proxies=["a.SrcA1"])
        run.apply_layers("StaticProxy/src_2")       # Change source code
        run.rerun(static_proxies=["a.SrcA2"])
        run.apply_layers("base")                    # Remove all
        run.rerun()

    @skip("#5293")
    def test_build_python_3(self):
        self.RunGradle("base", "StaticProxy/build_python_3", static_proxies=["a.ReqsA1"])


class License(GradleTestCase):
    def test_empty_key(self):
        run = self.RunGradle("base", key="", succeed=False)
        self.assertInLong("Chaquopy license verification failed", run.stderr)

        run.apply_layers("License/demo")
        run.rerun(licensed_id="com.chaquo.python.demo")

        run.apply_layers("base")
        run.rerun(succeed=False)

        run.apply_key(None)
        run.rerun(licensed_id=None)

    def test_key(self):
        run = self.RunGradle("base")

        run.apply_key("invalid")
        run.rerun(succeed=False)
        self.assertInLong("Chaquopy license verification failed", run.stderr)

        run.apply_key("AU5-6D8smj5fE6b53i9P7czOLV1L4Gf8W1L6RB_qkOQr")
        run.rerun(licensed_id="com.chaquo.python.test")

        run.apply_key(None)
        run.rerun(licensed_id=None)

    # There should be no way to produce a bad ticket via the plugin, but it could be done by
    # deliberate tampering.
    def test_bad_ticket(self):
        self.check_bad_ticket("valid.txt", "com.chaquo.python.test",
                              "Ticket is for 'com.chaquo.python.demo', but this app is "
                              "'com.chaquo.python.test'")
        self.check_bad_ticket("invalid.txt", "com.chaquo.python.test",
                              "VerificationError")

    def check_bad_ticket(self, ticket_filename, app_id, error):
        ticket_path = join(integration_dir, "data/License/tickets", ticket_filename)
        process = subprocess.Popen(["python", join(repo_root, "server/license/check_ticket.py"),
                                    "--ticket", ticket_path, "--app", app_id],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        self.assertNotEqual(0, process.wait())
        self.assertInLong(error, stderr)


integration_dir = abspath(dirname(__file__))
repo_root = abspath(join(integration_dir, "../../../../.."))


class RunGradle(object):
    @kwonly_defaults
    def __init__(self, test, key=None, *layers, **kwargs):
        self.test = test

        module, cls, func = test.id().split(".")
        self.run_dir = join(repo_root, "product/gradle-plugin/build/test/integration", cls, func)
        if os.path.exists(self.run_dir):
            rmtree(self.run_dir)

        self.project_dir = join(self.run_dir, "project")
        os.makedirs(self.project_dir)
        self.apply_layers(*layers)
        self.apply_key(key)

        self.rerun(**kwargs)

    def apply_layers(self, *layers):
        for layer in layers:
            copy_tree(join(integration_dir, "data", layer), self.project_dir,
                      preserve_times=False)  # https://github.com/gradle/gradle/issues/2301
            if layer == "base":
                self.apply_layers("base-" + os.environ["AGP_VERSION"])

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
        status, self.stdout, self.stderr = self.run_gradle(variants)

        if status == 0:
            if succeed is False:  # (succeed is None) means we don't care
                self.dump_run("run unexpectedly succeeded")

            # TODO #5180 Android plugin version 3 adds an extra variant directory below "apk".
            for variant in variants:
                outputs_apk_dir = join(self.project_dir, "app/build/outputs/apk")
                apk_file = join(outputs_apk_dir, "app-{}.apk".format(variant))  # Android plugin 2.x
                if not os.path.isfile(apk_file):
                    apk_file = join(outputs_apk_dir, variant.replace("-", "/"),
                                    "app-{}.apk".format(variant))  # Android plugin 3.x

                apk_dir = join(self.run_dir, "apk", variant)
                if os.path.exists(apk_dir):
                    rmtree(apk_dir)
                os.makedirs(apk_dir)
                ZipFile(apk_file).extractall(apk_dir)
                self.check_apk(apk_dir, **kwargs)

            # Run a second time to check all tasks are considered up to date.
            first_msg = "\n=== FIRST RUN STDOUT ===\n" + self.stdout
            status, self.stdout, self.stderr = self.run_gradle(variants)
            if status != 0:
                self.dump_run("exit status {}".format(status))
            self.test.assertInLong(":app:extractPythonBuildPackages UP-TO-DATE", self.stdout,
                                   msg=first_msg)
            for variant in variants:
                for suffix in ["Requirements", "Sources", "Ticket", "Assets", "JniLibs"]:
                    msg = task_name(":app:generate", variant, "Python" + suffix) + " UP-TO-DATE"
                    self.test.assertInLong(msg, self.stdout, msg=first_msg)

        else:
            if succeed:
                self.dump_run("exit status {}".format(status))

    def run_gradle(self, variants):
        os.chdir(self.project_dir)
        # --info explains why tasks were not considered up to date.
        # --console plain prevents output being truncated by a "String index out of range: -1"
        #   error on Windows.
        gradlew = "gradlew.bat" if sys.platform.startswith("win") else "./gradlew"
        process = subprocess.Popen([gradlew, "--stacktrace", "--info", "--console", "plain"] +
                                   [task_name(":app:assemble", v) for v in variants],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return process.wait(), stdout, stderr

    @kwonly_defaults
    def check_apk(self, apk_dir, abis=["x86"], requirements=[], static_proxies=[],
                  licensed_id=None):
        asset_dir = join(apk_dir, "assets/chaquopy")

        # Python source
        app_zip_actual = ZipFile(join(asset_dir, "app.zip"))
        # If app/src/main/python didn't already exist, the plugin should have created it.
        app_zip_expected = ZipFile(shutil.make_archive(
            join(self.run_dir, "app-expected"), "zip",
            join(self.project_dir, "app/src/main/python")))
        self.test.assertEqual(set(filelist(app_zip_expected)), set(filelist(app_zip_actual)))
        for name in filelist(app_zip_expected):
            self.test.assertEqual(app_zip_expected.getinfo(name).CRC,
                                  app_zip_actual.getinfo(name).CRC,
                                  name)

        # Python requirements
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
        classes = dex_classes(join(apk_dir, "classes.dex"))
        self.test.assertIn("com.chaquo.python.Python", classes)

        # Static proxies
        self.test.assertEqual(set(("static_proxy." + c) for c in static_proxies),
                              set(filter(lambda x: x.startswith("static_proxy"), classes)))

        # Licensing
        ticket_filename = join(asset_dir, "ticket.txt")
        if licensed_id:
            subprocess.check_call(["python", join(repo_root, "server/license/check_ticket.py"),
                                   "--quiet", "--ticket", ticket_filename, "--app", licensed_id])
        else:
            self.test.assertEqual(os.stat(ticket_filename).st_size, 0)

    def dump_run(self, msg):
        self.test.fail(msg + "\n" +
                       "=== STDOUT ===\n" + self.stdout +
                       "=== STDERR ===\n" + self.stderr)


def dex_classes(dex_filename):
    # The following properties file should be created manually. It's also used in
    # runtime/build.gradle.
    props = Properties()
    props.load(open(join(repo_root, "product/local.properties")))
    build_tools_dir = join(props["sdk.dir"].data, "build-tools")
    newest_ver = sorted(os.listdir(build_tools_dir))[-1]
    dexdump = subprocess.check_output([join(build_tools_dir, newest_ver, "dexdump"),
                                       dex_filename])
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

    return (prefix +
            "".join(cap_first(word) for word in variant.split("-")) +
            cap_first(suffix))


# shutil.make_archive doesn't create entries for directories in old versions of Python
# (https://bugs.python.org/issue24982).
def filelist(zip_file):
    return [name for name in zip_file.namelist() if not name.endswith("/")]


# shutil.rmtree is unreliable on MSYS2: it frequently fails with Windows error 145 (directory
# not empty), even though it has already removed everything from that directory.
def rmtree(path):
    subprocess.check_call(["rm", "-rf", path])


del GradleTestCase
