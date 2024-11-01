import json
import os
from os.path import abspath, dirname, join
import subprocess
import sys

from .test_utils import FilterWarningsCase

static_proxy_dir = abspath(dirname(__file__))
data_dir = join(static_proxy_dir, "data")
main_python_dir = abspath(join(static_proxy_dir, "../../../main/python"))
os.environ["PYTHONPATH"] = main_python_dir


class TestStaticProxy(FilterWarningsCase):

    maxDiff = None

    def test_find_module(self):
        self.run_json("nonexistent", "file", False, "nonexistent' does not exist")
        self.run_json("errors/empty.py", "file", False, "errors/empty.py' is not a directory")

        self.run_json(["find_module/path1", "find_module/path2"], ["a", "b", "c"],
                      expected="find_module/12.json")
        self.run_json(["find_module/path2", "find_module/path1"], ["a", "b", "c"],
                      expected="find_module/21.json")

        self.run_json("find_module/path3", "mod1")          # Exists as both module and package
        self.run_json("find_module/path3", "mod1.mod1a")
        self.run_json("find_module/path3", "mod99", False, "Module not found: mod99")
        self.run_json("find_module/path3", "empty", False, "Module not found: empty")
        self.run_json("find_module/path3", "no_init_py.mod", False,
                      "Module not found: no_init_py.mod")

    def test_encoding(self):
        self.run_json("encoding", "utf8")
        self.run_json("encoding", "utf8_identifiers")
        self.run_json("encoding", "big5_marked")  # PEP 263
        self.run_json("encoding", "big5_unmarked", False,
                      "'utf-?8' codec can't decode byte 0xa4", re=True)

    def test_errors(self):
        for name in ["empty", "no_proxies", "conditional"]:
            self.run_json("errors", name, False, name + ".py: no static_proxy classes found")

        self.run_json("errors", "syntax", False, "syntax.py:3:5: invalid syntax")
        self.run_json("errors", "syntax_py2", False,
                      f"syntax_py2.py:1:{7 if sys.version_info < (3, 10) else 1}"
                      f": Missing parentheses in call to 'print'")

        for name in ["starargs", "kwargs"]:
            self.run_json("errors", name, False,
                          name + ".py:6:9: *args and **kwargs are not supported here")

    def test_bindings(self):
        self.run_json("bindings", "import_from")
        self.run_json("bindings", "import_module")
        self.run_json("bindings", "import_module_as")
        self.run_json("bindings", "late", False,
                      "late.py:4:22: cannot resolve 'C' (binding not found)")
        self.run_json("bindings", "del", False,
                      "del.py:7:22: cannot resolve 'Class1' (binding not found)")
        self.run_json("bindings", "class", False,
                      r"class.py:7:22: cannot resolve 'C' \(bound at .*class.py:4:1\)", re=True)
        self.run_json("bindings", "def", False,
                      r"def.py:7:22: cannot resolve 'f' \(bound at .*def.py:4:1\)", re=True)
        self.run_json("bindings", "assign", False,
                      r"assign.py:6:22: cannot resolve 'C' \(bound at .*assign.py:4:1\)", re=True)
        self.run_json("bindings", "assign_list", False, "assign_list.py:6:22: cannot resolve 'C' "
                      r"\(bound at .*assign_list.py:4:4\)", re=True)
        self.run_json("bindings", "assign_list_recursive", False, "assign_list_recursive.py:6:22: "
                      r"cannot resolve 'C' \(bound at .*assign_list_recursive.py:4:8\)", re=True)
        self.run_json("bindings", "assign_aug", False, "assign_aug.py:7:22: cannot resolve 'C' "
                      r"\(bound at .*assign_aug.py:5:1\)", re=True)

    def test_bindings_py3(self):
        self.run_json("bindings", "def_async", False,
                      (r"def_async.py:6:22: cannot resolve 'x' "
                       r"\(bound at .*def_async.py:4:1\)"), re=True)
        self.run_json("bindings", "assign_ann", False,
                      (r"assign_ann.py:6:22: cannot resolve 'x' "
                       r"\(bound at .*assign_ann.py:4:1\)"), re=True)

    def test_header(self):
        self.run_json("header", "bases")
        self.run_json("header", "package")
        self.run_json("header", "modifiers")

    def test_constructor(self):
        self.run_json("constructor", "constructor")
        self.run_json("constructor", "name", False,
                      "name.py:5:6: @constructor can only be used on __init__")
        self.run_json("constructor", "return", False, "return.py:5:6: constructor() takes "
                      "1 positional argument but 2 were given")

    def test_method(self):
        self.run_json("method", "return")
        self.run_json("method", "args")
        self.run_json("method", "throws")
        self.run_json("method", "modifiers")
        self.run_json("method", "overload")
        self.run_json("method", "init_method", False,
                      "init_method.py:5:6: @method cannot be used on __init__")
        self.run_json("method", "init_override", False,
                      "init_override.py:5:6: @Override cannot be used on __init__")
        self.run_json("method", "missing_brackets", False, r"missing_brackets.py:5:6: 'arg_types' "
                      r"must be \(<(type|class) 'list'>, <(type|class) 'tuple'>\)", re=True)
        self.run_json("method", "missing_args", False, r"missing_args.py:5:6: method\(\) "
                      r"(takes at least 2 arguments|missing 1 required positional argument)",
                      re=True)

    def run_json(self, path, modules, succeed=True, expected=None, **kwargs):
        if isinstance(path, str):
            path = [path]
        if isinstance(modules, str):
            modules = [modules]
        if succeed and (expected is None):
            assert len(path) == 1 and len(modules) == 1
            expected = join(path[0], modules[0].replace(".", "/")) + ".json"

        process = subprocess.Popen(
            [sys.executable,
             "-m", "chaquopy.static_proxy",
             "--path", os.pathsep.join(join(data_dir, d) for d in path),
             "--json"] + modules,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        stdout, stderr = process.communicate()

        status = process.wait()
        if status == 0:
            if not succeed:
                self.dump_run("run unexpectedly succeeded", stdout, stderr)
            if stderr:
                # Probably a DeprecationWarning or similar.
                self.dump_run("succeeded but wrote to stderr", stdout, stderr)
            try:
                actual = json.loads(stdout)
            except ValueError:
                print("Invalid output\n" + stdout)
                raise
            with open(join(data_dir, expected), "rb") as expected_file:
                self.assertEqual(json.loads(expected_file.read().decode("utf-8")), actual)
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
                self.assertRegex(b, a)
            else:
                self.assertIn(a, b)
        except AssertionError:
            raise AssertionError("{} '{}' not found in:\n{}"
                                 .format(("regexp" if re else "string"), a, b))
