from __future__ import absolute_import, division, print_function

from distutils.dir_util import copy_tree
from kwonly_args import *
import os
from os.path import abspath, dirname, join
import shutil
import subprocess
from unittest import TestCase
from zipfile import ZipFile


# FIXME
# Wrong python version
# Wrong ABIs
# Override by flavor
# Override by multi-flavor
# up to date checks on tasks


class GradleTestCase(TestCase):
    def assertInLong(self, a, b):
        try:
            TestCase.assertIn(self, a, b)
        except AssertionError:
            raise AssertionError("'{}' not found in:\n{}".format(a, b))


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


data_dir  = abspath(join(dirname(__file__), "data"))
repo_root = abspath(join(dirname(__file__), "../../../../.."))
build_dir = abspath(join(repo_root, "product/gradle-plugin/build/integrationTest"))
demo_dir = abspath(join(repo_root, "demo"))


class RunGradle(object):
    @kwonly_defaults
    def __init__(self, succeed=True, *data_layers):
        run_dir = join(build_dir, "+".join(data_layers))
        if os.path.exists(run_dir):
            shutil.rmtree(run_dir)

        project_dir = join(run_dir, "project")
        os.makedirs(project_dir)
        shutil.copy(join(demo_dir, "local.properties"), project_dir)
        for d in data_layers:
            copy_tree(join(data_dir, d), project_dir)

        os.chdir(project_dir)
        # TODO #5184 Windows-specific
        process = subprocess.Popen(["gradlew.bat", ":app:assembleDebug"],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.stdout, self.stderr = process.communicate()
        if process.wait() == 0:
            if not succeed:
                dump_run(self, "run unexpectedly succeeded")
            # TODO #5180 Android plugin version 3 adds an extra "debug" directory below "apk".
            apk_file = join(project_dir, "app/build/outputs/apk/app-debug.apk")
            self.apk = join(run_dir, "apk")
            os.makedirs(self.apk)
            ZipFile(apk_file).extractall(self.apk)
        else:
            if succeed:
                dump_run(self, "run failed")


def dump_run(run, msg):
    raise AssertionError(msg + "\n" +
                         "=== STDOUT ===\n" + run.stdout +
                         "=== STDERR ===\n" + run.stderr)


del GradleTestCase
