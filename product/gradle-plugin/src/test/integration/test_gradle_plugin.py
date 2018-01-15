from __future__ import absolute_import, division, print_function

from distutils.dir_util import copy_tree
import distutils.util
from jproperties import Properties
import json
from kwonly_args import kwonly_defaults
import os
from os.path import abspath, dirname, join
import re
import subprocess
import sys
from unittest import skip, TestCase
from zipfile import ZipFile, ZIP_STORED


class GradleTestCase(TestCase):
    longMessage = True

    def RunGradle(self, *args, **kwargs):
        return RunGradle(self, *args, **kwargs)

    # Prints b as a multi-line string rather than a repr().
    def assertInLong(self, a, b, re=False, msg=None):
        try:
            if re:
                self.assertRegexpMatches(b, a)
            else:
                self.assertIn(a, b)
        except self.failureException:
            msg = self._formatMessage(msg, "{}'{}' not found in:\n{}".format
                                      ("regex " if re else "", a, b))
            raise self.failureException(msg)


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
        self.assertInLong("requires Android Gradle plugin version 2.2.0", run.stderr)

    def test_untested(self):
        run = self.RunGradle("base", "AndroidPlugin/untested",
                             succeed=None)  # 3.1.0-alpha01 fails on Linux, don't know why.
        self.assertInLong("not been tested with Android Gradle plugin versions beyond 3.0.1",
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
        self.assertInLong("debug: invalid Python version '2.7.99'. Available versions are "
                          "[2.7.10, 2.7.14, 3.6.3]", run.stderr)

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
        run.rerun(app={"one.py": "one", "package/submodule.py": "submodule"})
        run.apply_layers("PythonSrc/2")                                 # Modify
        run.rerun(app={"one.py": "one modified", "package/submodule.py": "submodule"})
        os.remove(join(run.project_dir, "app/src/main/python/one.py"))  # Remove
        run.rerun(app={"package/submodule.py": "submodule"})

    def test_variant(self):
        self.RunGradle("base", "PythonSrc/variant",
                       variants={"red-debug": dict(app={"common.py": "common",
                                                        "color.py": "red"}),
                                 "blue-debug": dict(app={"common.py": "common",
                                                         "color.py": "blue"})})

    def test_conflict(self):
        variants = {"red-debug": dict(app={"common.py": "common main", "color.py": "red"}),
                    "blue-debug": dict(app={"common.py": "common main", "color.py": "blue"})}
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
        self.RunGradle("base", "PythonSrc/set_root", app={"one.py": "one main2"},
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


class BuildPython(GradleTestCase):
    def test_default(self):
        self.RunGradle("base", "BuildPython/default", requirements=["apple"])

    def test_invalid(self):
        run = self.RunGradle("base", "BuildPython/invalid", succeed=False)
        self.assertInLong("problem occurred starting process 'command 'pythoninvalid''", run.stderr)

    def test_variant(self):
        run = self.RunGradle("base", "BuildPython/variant",
                             requirements=["apple"], variants=["good-debug"])
        run.rerun(variants=["bad-debug"], succeed=False)
        self.assertInLong("problem occurred starting process 'command 'pythoninvalid''", run.stderr)

    def test_variant_merge(self):
        run = self.RunGradle("base", "BuildPython/variant_merge",
                             requirements=["apple"], variants=["good-debug"])
        run.rerun(variants=["bad-debug"], succeed=False)
        self.assertInLong("problem occurred starting process 'command 'pythoninvalid''", run.stderr)


# Use these as mixins to run a set of tests once each for python2 and python3.
class BuildPythonCase(TestCase):
    def setUp(self):
        super(BuildPythonCase, self).setUp()
        os.environ["buildPython"] = self.buildPython

    def tearDown(self):
        del os.environ["buildPython"]
        super(BuildPythonCase, self).tearDown()

class BuildPython2(BuildPythonCase):
    buildPython = "python2"

class BuildPython3(BuildPythonCase):
    buildPython = "python3"


class PythonReqs(GradleTestCase):
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

    def test_install_variant(self):
        self.RunGradle("base", "PythonReqs/install_variant",
                       variants={"red-debug":  {"requirements": ["apple"]},
                                 "blue-debug": {"requirements": ["bravo"]}})

    def test_install_variant_merge(self):
        self.RunGradle("base", "PythonReqs/install_variant_merge",
                       variants={"red-debug":  {"requirements": ["apple"]},
                                 "blue-debug": {"requirements": ["apple", "bravo"]}})

    def test_options_variant(self):
        self.RunGradle("base", "PythonReqs/options_variant",
                       variants={"red-debug":  {"requirements": ["apple"]},
                                 "blue-debug": {"requirements": ["apple_local"]}})

    def test_options_variant_merge(self):
        self.RunGradle("base", "PythonReqs/options_variant_merge",
                       variants={"red-debug":  {"requirements": ["alpha", "alpha_dep"]},
                                 "blue-debug": {"requirements": ["alpha"]}})

    def test_reqs_file(self):
        run = self.RunGradle("base", "PythonReqs/reqs_file", requirements=["apple", "bravo"])
        run.apply_layers("PythonReqs/reqs_file_2")
        run.rerun(requirements=["alpha", "alpha_dep", "bravo"])

    def test_wheel_file(self):
        run = self.RunGradle("base", "PythonReqs/wheel_file", requirements=["apple"])
        run.apply_layers("PythonReqs/wheel_file_2")
        run.rerun(requirements=["apple2"])

    def test_sdist_file(self):
        run = self.RunGradle("base", "PythonReqs/sdist_file", succeed=False)
        self.assertInLong("alpha_dep-0.0.1.tar.gz: Chaquopy does not support sdist packages",
                          run.stderr)

    def test_editable(self):
        run = self.RunGradle("base", "PythonReqs/editable", succeed=False)
        self.assertInLong("Invalid python.pip.install format: '-e src'", run.stderr)

    def test_wheel_index(self):
        # If testing on another platform, add it to the list below, and add corresponding
        # wheels to packages/dist.
        self.assertIn(distutils.util.get_platform(), ["linux-x86_64", "mingw"])

        # This test has build platform wheels for version 0.2, and an Android wheel for version
        # 0.1, to test that pip always picks the target platform, not the workstation platform.
        run = self.RunGradle("base", "PythonReqs/wheel_index_1",
                             requirements=["native1_android_15_x86"])

        # This test only has build platform wheels.
        run.apply_layers("PythonReqs/wheel_index_2")
        run.rerun(succeed=False)
        self.assertInLong("No matching distribution found for native2", run.stderr)

    def test_sdist_index(self):
        # This test has an sdist for version 0.2 and a wheel for version 0.1, to test that pip
        # ignores the sdist.
        run = self.RunGradle("base", "PythonReqs/sdist_index_1",
                             requirements=["native3_android_15_x86"])

        # This test has only an sdist.
        run.apply_layers("PythonReqs/sdist_index_2")
        run.rerun(succeed=False)
        self.assertInLong("No matching distribution found for native4 "
                          "(NOTE: Chaquopy only supports wheels, not sdist packages)", run.stderr)

    def test_multi_abi(self):
        # This is not the same as the filename pattern used in our real wheels, but the point
        # is to test that the multi-ABI merging works correctly.
        self.RunGradle("base", "PythonReqs/multi_abi_1", abis=["armeabi-v7a", "x86"],
                       requirements=["apple",             # Pure Python requirement
                                     "multi_abi_1_pure",  # Identical content in both ABIs
                                     "multi_abi_1_armeabi_v7a.pyd", "multi_abi_1_x86.pyd"])

    def test_multi_abi_variant(self):
        variants = {"armeabi_v7a-debug": {"abis": ["armeabi-v7a"],
                                          "requirements": ["apple", "multi_abi_1_pure",
                                                           "multi_abi_1_armeabi_v7a.pyd"]},
                    "x86-debug":         {"abis": ["x86"],
                                          "requirements": ["apple", "multi_abi_1_pure",
                                                           "multi_abi_1_x86.pyd"]}}
        self.RunGradle("base", "PythonReqs/multi_abi_variant", variants=variants)

    def test_multi_abi_clash(self):
        run = self.RunGradle("base", "PythonReqs/multi_abi_clash", succeed=False)
        self.assertInLong("file 'multi_abi_1_pure/__init__.py' from ABIs \['armeabi-v7a'\] .* "
                          "does not match copy from 'x86'", run.stderr, re=True)

    # ABIs should be installed in alphabetical order. (In the order specified is not possible
    # because the Android Gradle plugin keeps abiFilters in a HashSet.)
    def test_multi_abi_order(self):
        # armeabi-v7a will install a pure-Python wheel, so the requirement will not be
        # installed again for x86, even though an x86 wheel is available.
        run = self.RunGradle("base", "PythonReqs/multi_abi_order_1", abis=["armeabi-v7a", "x86"],
                             requirements=["multi_abi_order_pure"])

        # armeabi-v7a will install a native wheel, so the requirement will be installed again
        # for x86, which will select the pure-Python wheel.
        run.apply_layers("PythonReqs/multi_abi_order_2")
        run.rerun(abis=["armeabi-v7a", "x86"],
                  requirements=["multi_abi_order_armeabi_v7a.pyd", "multi_abi_order_pure"])

class PythonReqs2(PythonReqs, BuildPython2):
    pass
class PythonReqs3(PythonReqs, BuildPython3):
    pass
del PythonReqs


class StaticProxy(GradleTestCase):
    def test_change(self):
        run = self.RunGradle("base", "StaticProxy/reqs", requirements=["chaquopy_test"],
                             classes=["a.ReqsA1", "b.ReqsB1"])
        app = ["chaquopy_test/__init__.py", "chaquopy_test/a.py"]
        run.apply_layers("StaticProxy/src_1")       # Src should take priority over reqs.
        run.rerun(requirements=["chaquopy_test"], app=app, classes=["a.SrcA1", "b.ReqsB1"])
        run.apply_layers("StaticProxy/src_only")    # Remove reqs
        run.rerun(app=app, classes=["a.SrcA1"])
        run.apply_layers("StaticProxy/src_2")       # Change source code
        run.rerun(app=app, classes=["a.SrcA2"])
        run.apply_layers("base")                    # Remove all
        run.rerun(app=app)

    def test_variant(self):
        self.RunGradle("base", "StaticProxy/variant",
                       requirements=["chaquopy_test"],
                       variants={"red-debug":  {"classes": ["a.ReqsA1"]},
                                 "blue-debug": {"classes": ["b.ReqsB1"]}})

    def test_variant_merge(self):
        self.RunGradle("base", "StaticProxy/variant_merge",
                       requirements=["chaquopy_test"],
                       variants={"red-debug":  {"classes": ["a.ReqsA1"]},
                                 "blue-debug": {"classes": ["a.ReqsA1", "b.ReqsB1"]}})

class StaticProxy2(StaticProxy, BuildPython2):
    pass
class StaticProxy3(StaticProxy, BuildPython3):
    pass
del StaticProxy


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

        module, cls, func = re.search(r"^(\w+)\.(\w+)\.test_(\w+)$", test.id()).groups()
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

            for variant in variants:
                outputs_apk_dir = join(self.project_dir, "app/build/outputs/apk")
                apk_filename = join(outputs_apk_dir,
                                    "app-{}.apk".format(variant))       # Android plugin 2.x
                if not os.path.isfile(apk_filename):
                    apk_filename = join(outputs_apk_dir, variant.replace("-", "/"),
                                        "app-{}.apk".format(variant))   # Android plugin 3.x

                apk_file = ZipFile(apk_filename)
                for info in apk_file.infolist():
                    if re.search(r"^assets/chaquopy/.*\.zip$", info.filename):
                        self.test.assertEqual(ZIP_STORED, info.compress_type, info.filename)

                apk_dir = join(self.run_dir, "apk", variant)
                if os.path.exists(apk_dir):
                    rmtree(apk_dir)
                os.makedirs(apk_dir)
                apk_file.extractall(apk_dir)

                merged_kwargs = kwargs.copy()
                if isinstance(variants, dict):
                    merged_kwargs.update(variants[variant])
                self.check_apk(apk_dir, **merged_kwargs)

            # Run a second time to check all tasks are considered up to date.
            first_msg = "\n=== FIRST RUN STDOUT ===\n" + self.stdout
            status, self.stdout, self.stderr = self.run_gradle(variants)
            if status != 0:
                self.dump_run("exit status {}".format(status))
            self.test.assertInLong(":app:extractPythonBuildPackages UP-TO-DATE", self.stdout,
                                   msg=first_msg)
            for variant in variants:
                for verb, obj in [("generate", "Requirements"), ("merge", "Sources"),
                                  ("generate", "Proxies"), ("generate", "Ticket"),
                                  ("generate", "Assets"), ("generate", "JniLibs")]:
                    msg = task_name(verb, variant, "Python" + obj) + " UP-TO-DATE"
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
                                   [task_name("assemble", v) for v in variants],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return process.wait(), stdout, stderr

    @kwonly_defaults
    def check_apk(self, apk_dir, abis=["x86"], version="2.7.14", classes=[], app=[],
                  requirements=[], extract_packages=[], licensed_id=None):
        asset_dir = join(apk_dir, "assets/chaquopy")
        self.test.assertEqual(["app.zip", "bootstrap-native", "bootstrap.zip", "build.json",
                               "cacert.pem", "requirements.zip", "stdlib-native", "stdlib.zip",
                               "ticket.txt"],
                              sorted(os.listdir(asset_dir)))

        # Python source
        app_zip = ZipFile(join(asset_dir, "app.zip"))
        # If app/src/main/python didn't already exist, the plugin should have created it.
        self.test.assertEqual(sorted(app), sorted(name for name in app_zip.namelist()
                                                  if not name.endswith("/")))
        if isinstance(app, dict):
            for name, text in app.items():
                self.test.assertEqual(text, app_zip.read(name).decode().strip())

        # Python requirements
        reqs_zip = ZipFile(join(asset_dir, "requirements.zip"))
        self.test.assertEqual(set(requirements),
                              set(path.partition("/")[0] for path in reqs_zip.namelist()))

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
        self.test.assertEqual([abi + ".zip" for abi in sorted(abis)],
                              sorted(os.listdir(stdlib_native_dir)))
        for abi in abis:
            stdlib_native_zip = ZipFile(join(stdlib_native_dir, abi + ".zip"))
            self.test.assertEqual(["_multiprocessing.so", "_socket.so", "_sqlite3.so",
                                   "_ssl.so", "pyexpat.so", "unicodedata.so"],
                                  sorted(stdlib_native_zip.namelist()))

        # JNI libs
        self.test.assertEqual(sorted(abis), sorted(os.listdir(join(apk_dir, "lib"))))
        ver_suffix = version.rpartition(".")[0]
        if ver_suffix.startswith("3"):
            ver_suffix += "m"
        for abi in abis:
            self.test.assertEqual(["libchaquopy_java.so", "libcrystax.so",
                                   "libpython{}.so".format(ver_suffix)],
                                  sorted(os.listdir(join(apk_dir, "lib", abi))))

        # Chaquopy runtime library
        actual_classes = dex_classes(join(apk_dir, "classes.dex"))
        self.test.assertIn("com.chaquo.python.Python", actual_classes)

        # App Java classes
        self.test.assertEqual(sorted(("chaquopy_test." + c) for c in classes),
                              sorted(c for c in actual_classes if c.startswith("chaquopy_test")))

        # build.json
        DEFAULT_EXTRACT_PACKAGES = ["certifi"]
        with open(join(asset_dir, "build.json")) as build_json_file:
            build_json = json.load(build_json_file)
        self.test.assertEqual(["assets", "extractPackages", "version"], sorted(build_json))
        self.test.assertEqual(version, build_json["version"])
        self.test.assertEqual(sorted(extract_packages + DEFAULT_EXTRACT_PACKAGES),
                              sorted(build_json["extractPackages"]))

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

    return (":app:" + prefix +
            "".join(cap_first(word) for word in variant.split("-")) +
            cap_first(suffix))


# shutil.rmtree is unreliable on MSYS2: it frequently fails with Windows error 145 (directory
# not empty), even though it has already removed everything from that directory.
def rmtree(path):
    subprocess.check_call(["rm", "-rf", path])
