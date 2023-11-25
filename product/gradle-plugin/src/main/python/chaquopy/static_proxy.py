#!/usr/bin/env python3

# Do this as early as possible to minimize the chance of something else going wrong and causing
# a less comprehensible error message.
from .util import check_build_python
check_build_python()

import argparse
import ast
from contextlib import contextmanager
from datetime import datetime
from itertools import chain
import json
import os
from os.path import exists, isdir, isfile
import sys
import tokenize
import warnings

import attr
from attr.validators import instance_of, optional

from .util import CommandError

# Consistent output for tests
def join(*paths):
    return os.path.join(*paths).replace("\\", "/")


PRIMITIVES = ["void", "boolean", "byte", "short", "int", "long", "float", "double", "char"]
JAVA_ALL = (["static_proxy", "jarray", "constructor", "method", "Override"] +  # Only the names used
            [("j" + p) for p in PRIMITIVES])                                   # by this script.

def unwrap_if_primitive(name):
    PRIMITIVE_PREFIX = "java.j"
    if name.startswith(PRIMITIVE_PREFIX):
        primitive = name[len(PRIMITIVE_PREFIX):]
        if primitive in PRIMITIVES:
            return primitive
    return name


def main():
    # TODO: remove once our minimum buildPython version is Python 3.8.
    for message in [r".*use ast.Constant instead", r".*use value instead"]:
        warnings.filterwarnings("ignore", message, DeprecationWarning)

    args = parse_args()

    try:
        path = args.path.split(os.pathsep)
        for dirname in path:
            if not exists(dirname):
                raise CommandError("Path entry '{}' does not exist".format(dirname))
            elif not isdir(dirname):
                raise CommandError("Path entry '{}' is not a directory".format(dirname))

        classes = []
        for mod_name in args.modules:
            mod_filename = find_module(mod_name, path)
            classes += Module(mod_name, mod_filename).process()

        if args.json:
            print(json.dumps(classes, default=lambda c: attr.asdict(c), indent=4))
        if args.java:
            for cls in classes:
                write_java(args.java, cls)

    except CommandError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    except SyntaxError as e:
        print("{}:{}:{}: {}".format(e.filename, e.lineno, e.offset, e.msg), file=sys.stderr)
        print("Build Python is version {}.{}. If you are using syntax incompatible with this "
              "version, please edit the buildPython setting in build.gradle."
              .format(*sys.version_info[:2]), file=sys.stderr)
        sys.exit(1)


def parse_args():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--help", action="help", help=argparse.SUPPRESS)

    ap.add_argument("--path", default=".",
                    help=("Path to search for Python modules (default='%(default)s', "
                          "separator='{}')".format(os.pathsep)))
    ap.add_argument("modules", metavar="MODULE", nargs="+",
                    help="Python modules to process")

    output = ap.add_mutually_exclusive_group(required=True)
    output.add_argument("--java", metavar="DIR",
                        help="Generate Java source code in the given directory")
    output.add_argument("--json", action="store_true",
                        help="Generate JSON on stdout")

    return ap.parse_args()


def find_module(mod_name, path):
    words = mod_name.split(".")
    for root_dir in path:
        cur_dir = root_dir
        for i, word in enumerate(words):
            if i < (len(words) - 1):
                cur_dir = join(cur_dir, word)
                if not isfile(join(cur_dir, "__init__.py")):
                    break
            else:
                # Packages take priority over modules (https://stackoverflow.com/questions/4092395/)
                package_filename = join(cur_dir, word, "__init__.py")
                if isfile(package_filename):
                    return package_filename
                mod_filename = join(cur_dir, word + ".py")
                if isfile(mod_filename):
                    return mod_filename

    raise CommandError("Module not found: " + mod_name)


# Only user-supplied fields are validated.
@attr.s
class Class(object):
    name = attr.ib()
    module = attr.ib()
    extends = attr.ib(validator=optional(instance_of(str)))
    implements = attr.ib(validator=instance_of(tuple))
    package = attr.ib(validator=instance_of(str))
    modifiers = attr.ib(validator=instance_of(str))
    constructors = attr.ib()
    methods = attr.ib()


# Attrs constructors can't enforce keyword-only arguments, so we use wrapper functions.
def constructor(arg_types, *, modifiers="public", throws=None):
    if throws is None:
        throws = []
    return Constructor(arg_types, modifiers, throws)

@attr.s
class Constructor(object):
    arg_types = attr.ib(validator=instance_of((list, tuple)))
    modifiers = attr.ib(validator=instance_of(str))
    throws = attr.ib(validator=instance_of((list, tuple)))


def Override(return_type, arg_types, *, modifiers="public", throws=None, name):
    return method(return_type, arg_types, modifiers=("@Override " + modifiers),
                  throws=throws, name=name)

def method(return_type, arg_types, *, modifiers="public", throws=None, name):
    if throws is None:
        throws = []
    return Method(name, return_type, arg_types, modifiers, throws)

@attr.s
class Method(object):
    name = attr.ib()
    return_type = attr.ib(validator=instance_of(str))
    arg_types = attr.ib(validator=instance_of((list, tuple)))
    modifiers = attr.ib(validator=instance_of(str))
    throws = attr.ib(validator=instance_of((list, tuple)))


class Module(object):
    def __init__(self, name, filename):
        self.name = name
        self.filename = filename
        self.bindings = {}

    def process(self):
        classes = []
        root = ast.parse(tokenize.open(self.filename).read(), self.filename)

        # These are all the node types which can change global bindings. We map the bound name
        # to its fully-qualified name if it's a usable import, or otherwise to the node which
        # bound it so we can give a useful error if the name is passed to one of our functions.
        for node in root.body:
            if isinstance(node, (ast.FunctionDef if sys.version_info < (3, 5)
                                 else (ast.FunctionDef, ast.AsyncFunctionDef))):
                self.bindings[node.name] = node
            elif isinstance(node, ast.ClassDef):
                c = self.process_class(node)
                if c:
                    classes.append(c)
            elif isinstance(node, ast.Delete):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        del self.bindings[t.id]
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    self.process_assign(t)
            elif isinstance(node, (ast.AugAssign if sys.version_info < (3, 6)
                                   else (ast.AugAssign, ast.AnnAssign))):
                self.process_assign(node.target)
            elif isinstance(node, ast.Import):
                self.process_import(node.names, lambda name: name)
            elif isinstance(node, ast.ImportFrom):
                names = node.names
                if names[0].name == "*":
                    if node.module == "java":
                        names = [ast.alias(name, None) for name in JAVA_ALL]
                    else:
                        names = []

                if node.module and not node.level:  # Absolute import
                    self.process_import(names, lambda name: node.module + "." + name)
                else:                               # Relative import, not supported.
                    self.process_import(names, lambda name: node)

        if not classes:
            self.error(None, "{}: no static_proxy classes found. Class definitions and 'java' "
                       "module imports must appear unconditionally at the module top-level."
                       .format(self.filename))
        return classes

    def process_assign(self, target):
        if isinstance(target, ast.Name):
            self.bindings[target.id] = target
        elif isinstance(target, (ast.Tuple, ast.List)):
            for t in target.elts:
                self.process_assign(t)
        # Assignments to attributes and subscripts have no effect on global bindings.

    def process_import(self, names, get_binding):
        for alias in names:
            if alias.asname:
                key, value = alias.asname, alias.name
            else:
                key = value = alias.name.partition(".")[0]
            self.bindings[key] = get_binding(value)

    def process_class(self, node):
        # TODO allow static proxy classes as bases (#5283) and return, argument and throws
        # types (#5284).
        self.bindings[node.name] = node
        if node.bases:
            first_base = node.bases[0]
            if isinstance(first_base, ast.Call) and \
               self.lookup(first_base.func) == "java.static_proxy":
                return self.process_static_proxy(node, first_base)
        return None

    def process_static_proxy(self, cls, sp_call):
        def static_proxy(extends=None, *implements, package=None, modifiers="public"):
            if package is None:
                package = self.name
            return extends, implements, package, modifiers
        extends, implements, package, modifiers = self.call(static_proxy, sp_call)

        constructors = []
        methods = []
        for stmt in cls.body:
            if isinstance(stmt, ast.FunctionDef):
                for decor in stmt.decorator_list:
                    if isinstance(decor, ast.Call):
                        func = self.lookup(decor.func)
                        if func == "java.constructor":
                            if stmt.name != "__init__":
                                self.error(decor, "@constructor can only be used on __init__")
                            constructors.append(self.call(constructor, decor))
                        elif func in ["java.method", "java.Override"]:
                            func_simple = func[len("java."):]
                            if stmt.name == "__init__":
                                self.error(decor, "@{} cannot be used on __init__"
                                           .format(func_simple))
                            methods.append(self.call(globals()[func_simple], decor, name=stmt.name))

        try:
            return Class(cls.name, self.name, extends, implements, package, modifiers,
                         constructors, methods)
        except TypeError as e:
            self.error(cls, type_error_msg(e))

    # Calls the given function with the Call node's arguments, which must all be either
    # literals, or expressions which can be turned into strings by resolve(). Additional
    # keyword arguments may also be passed through.
    def call(self, function, call, **kwargs):
        if self.has_starargs(call) or self.has_kwargs(call):
            self.error(call, "*args and **kwargs are not supported here")
        args = [self.evaluate(a) for a in call.args]
        kwargs.update((kw.arg, self.evaluate(kw.value)) for kw in call.keywords)
        try:
            result = function(*args, **kwargs)
        except TypeError as e:
            self.error(call, type_error_msg(e))
        return result

    def has_starargs(self, call):
        if sys.version_info < (3, 5):
            return bool(call.starargs)
        else:
            return any(isinstance(a, ast.Starred) for a in call.args)

    def has_kwargs(self, call):
        if sys.version_info < (3, 5):
            return bool(call.kwargs)
        else:
            return any(kw.arg is None for kw in call.keywords)

    def evaluate(self, expr):
        if isinstance(expr, ast.Num):
            return expr.n
        elif isinstance(expr, ast.Str):
            return expr.s
        elif isinstance(expr, ast.NameConstant):  # True, False, None
            return expr.value
        elif isinstance(expr, ast.Name):
            return self.resolve(expr)
        elif isinstance(expr, (ast.Attribute, ast.Call)):
            return self.resolve(expr)
        elif isinstance(expr, (ast.List, ast.Tuple)):
            return [self.evaluate(e) for e in expr.elts]
        # The only other literal node types are Dict and Set, which are not currently accepted
        # by any of our functions.
        else:
            self.error(expr, type(expr).__name__ + " expression is not supported here")

    def lookup(self, expr):
        try:
            return self.resolve(expr)
        except CommandError:
            return None

    # Converts an expression node to a fully-qualified name or Java type string.
    def resolve(self, expr):
        what = "expression"
        if isinstance(expr, ast.Attribute):
            return unwrap_if_primitive(self.resolve(expr.value) + "." + expr.attr)
        elif isinstance(expr, ast.Name):
            result = self.bindings.get(expr.id)
            if isinstance(result, str):
                return unwrap_if_primitive(result)
            else:
                what = "'{}'".format(expr.id)
                if result is None:
                    what += " (binding not found)"
                else:
                    what += " (bound at {})".format(self.where(result))
        elif isinstance(expr, ast.Call) and self.lookup(expr.func) == "java.jarray":
            def jarray(element_type):
                return element_type
            return self.call(jarray, expr) + "[]"

        self.error(expr, "cannot resolve {}. Java types must be imported unconditionally "
                   "at the module top-level.".format(what))

    def error(self, node, message):
        if node:
            message = self.where(node) + ": " + message
        raise CommandError(message)

    def where(self, node):
        return "{}:{}:{}".format(self.filename, node.lineno, node.col_offset + 1)


class write_java(object):
    def __init__(self, root_dirname, cls):
        pkg_dirname = join(root_dirname, cls.package.replace(".", "/"))
        if not isdir(pkg_dirname):
            os.makedirs(pkg_dirname)

        self.indent = 0
        with open(join(pkg_dirname, cls.name + ".java"), "w") as self.out_file:
            self.line("// Generated at {} with the command line:",
                      datetime.now().astimezone().isoformat(timespec="seconds"))
            self.line("// {}", " ".join(sys.argv[1:]))
            self.line()
            self.line("package {};", cls.package)
            self.line()
            self.line("import com.chaquo.python.*;")
            self.line("import java.lang.reflect.*;")
            self.line("import static com.chaquo.python.PyObject._chaquopyCall;")
            self.line()
            self.line('@SuppressWarnings("deprecation")')
            with self.block("{} class {} {} {}", cls.modifiers, cls.name,
                            self.format_optional("extends", cls.extends),
                            self.format_list("implements", cls.implements + ("StaticProxy",))):
                with self.block("static"):
                    self.line('Python.getInstance().getModule("{}").get("{}");'
                              .format(cls.module, cls.name))
                self.line()
                for method in chain(cls.constructors or [constructor([])], cls.methods):
                    self.method(cls, method)
                    self.line()

                self.line("public {}(PyCtorMarker pcm) {{}}".format(cls.name))
                self.line("private PyObject _chaquopyDict;")
                self.line("public PyObject _chaquopyGetDict() { return _chaquopyDict; }")
                self.line("public void _chaquopySetDict(PyObject dict) { _chaquopyDict = dict; }")

    def method(self, cls, method):
        is_ctor = isinstance(method, Constructor)
        header = "{} {} {}({}) {}".format(
            method.modifiers,
            "" if is_ctor else method.return_type,
            cls.name if is_ctor else method.name,
            self.format_list("{} arg{}".format(t, i) for i, t in enumerate(method.arg_types)),
            self.format_list("throws", method.throws))
        with self.block(header):
            self.line("PyObject result;")
            with self.handle_exceptions(method):
                args = (["this",
                        '"{}"'.format("__init__" if is_ctor else method.name)] +
                        ["arg{}".format(i) for i in range(len(method.arg_types))])
                self.line("result = _chaquopyCall({});".format(", ".join(args)))

            return_type = "void" if is_ctor else method.return_type
            toJava = "result.toJava({}.class)".format(return_type)
            if return_type == "void":
                self.line("if (result != null) {};".format(toJava))
            elif return_type in PRIMITIVES:
                self.line("return {};".format(toJava))
            else:
                self.line("return (result == null) ? null : {};".format(toJava))

    @contextmanager
    def handle_exceptions(self, method):
        if method.throws:
            with self.block("try"):
                yield
            with self.block("catch (UndeclaredThrowableException ute)"):
                with self.block("try"):
                    self.line("throw ute.getCause();")
                with self.block("catch ({} e)".format(" | ".join(method.throws))):
                    self.line("throw e;")
                with self.block("catch (Throwable e)"):
                    self.line("throw ute;")
        else:
            yield

    def format_list(self, *args):
        if len(args) == 1:
            prefix, l = "", args[0]
        else:
            prefix, l = args
        return self.format_optional(prefix, ", ".join(l))

    def format_optional(self, prefix, s):
        return (prefix + " " + s).strip() if s else ""

    @contextmanager
    def block(self, template="", *args):
        self.line(template.format(*args) + " {")
        self.indent += 4
        yield
        self.indent -= 4
        self.line("}")

    def line(self, template="", *args):
        s = template
        if args:
            s = s.format(*args)
        s = " ".join(s.split())  # Collapse consecutive spaces
        print((" " * self.indent) + s, file=self.out_file)


def type_error_msg(e):
    if (len(e.args) == 4) and isinstance(e.args[1], attr.Attribute):
        return e.args[0]
    else:
        return str(e)


if __name__ == "__main__":
    main()
