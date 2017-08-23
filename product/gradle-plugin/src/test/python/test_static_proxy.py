from __future__ import absolute_import, division, print_function

import json
import os
from os.path import abspath, dirname, join
import subprocess
from unittest import TestCase


test_python_dir = abspath(dirname(__file__))
data_dir = join(test_python_dir, "data/static_proxy")
main_python_dir = abspath(join(test_python_dir, "../../main/python"))
os.environ["PYTHONPATH"] = main_python_dir


class TestStaticProxy(TestCase):

    def test_errors(self):
        self.run_json("nonexistent", "file", False, "nonexistent' does not exist")
        self.run_json("errors/empty.py", "file", False, "errors/empty.py' is not a directory")
        self.run_json("errors", "empty", False, "No static_proxy classes found in .*errors/empty.py'")
        self.run_json("errors", "no_proxies", False,
                      "No static_proxy classes found in .*errors/no_proxies.py'")

    def test_simple(self):
        self.run_json("simple", "bases")

    def run_json(self, path, modules, succeed=True, expected=None):
        if isinstance(path, str): path = [path]
        if isinstance(modules, str): modules = [modules]
        if succeed and (expected is None):
            assert len(path) == 1 and len(modules) == 1
            expected = join(path[0], modules[0].replace(".", "/")) + ".json"

        process = subprocess.Popen \
            (["python", join(main_python_dir, "chaquopy/static_proxy.py"),
              "--path", os.pathsep.join(join(data_dir, d) for d in path),
              "--json"] + modules,
             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        status = process.wait()
        if status == 0:
            if not succeed:
                self.dump_run("run unexpectedly succeeded", stdout, stderr)
            try:
                result = json.loads(stdout)
            except ValueError:
                print("Invalid output\n" + stdout)
                raise
            self.assertEqual(result, json.load(open(join(data_dir, expected))))
        else:
            if succeed:
                self.dump_run("exit status {}".format(status), stdout, stderr)
            self.assertInLong(expected, stderr, re=True)

    def dump_run(self, msg, stdout, stderr):
        self.fail(msg + "\n" +
                   "=== STDOUT ===\n" + stdout +
                   "=== STDERR ===\n" + stderr)

    # Prints b as a multi-line string rather than a repr().
    def assertInLong(self, a, b, re=False):
        try:
            if re:
                self.assertRegexpMatches(b, a)
            else:
                self.assertIn(a, b)
        except AssertionError:
            raise AssertionError("'{}' not found in:\n{}".format(a, b))
