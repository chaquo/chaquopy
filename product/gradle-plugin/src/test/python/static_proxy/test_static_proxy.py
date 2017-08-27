from __future__ import absolute_import, division, print_function

import json
import os
from os.path import abspath, dirname, join
import subprocess
from unittest import TestCase


static_proxy_dir = abspath(dirname(__file__))
data_dir = join(static_proxy_dir, "data")
main_python_dir = abspath(join(static_proxy_dir, "../../../main/python"))
os.environ["PYTHONPATH"] = main_python_dir


class TestStaticProxy(TestCase):

    def test_find_module(self):
        self.run_json("nonexistent", "file", False, "nonexistent' does not exist")
        self.run_json("errors/empty.py", "file", False, "errors/empty.py' is not a directory")
        self.run_json(["find_module/path1", "find_module/path2"], ["a", "b", "c"],
                      True, "find_module/12.json")
        self.run_json(["find_module/path2", "find_module/path1"], ["a", "b", "c"],
                      True, "find_module/21.json")
        self.run_json("find_module/path3", "mod1")          # Exists as both module and package
        self.run_json("find_module/path3", "mod1.mod1a")
        self.run_json("find_module/path3", "mod99", False, "Module not found: mod99")

    def test_errors(self):
        self.run_json("errors", "empty", False,
                      "No static_proxy classes found in .*errors/empty.py'", re=True)
        self.run_json("errors", "no_proxies", False,
                      "No static_proxy classes found in .*errors/no_proxies.py'", re=True)
        self.run_json("errors", "syntax", False, "syntax.py:3:7: invalid syntax")

    def test_header(self):
        self.run_json("header", "bases")
        self.run_json("header", "bases_zero_args", False,
                      "bases_zero_args.py:4:8: static_proxy() takes at least 1 argument")
        self.run_json("header", "package")

    def run_json(self, path, modules, succeed=True, expected=None, **kwargs):
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
            self.assertInLong(expected, stderr, **kwargs)

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
            raise AssertionError("{} '{}' not found in:\n{}"
                                 .format(("regexp" if re else "string"), a, b))
