#!/usr/bin/env python

"""Copyright (c) 2017 Chaquo Ltd. All rights reserved."""

from __future__ import absolute_import, division, print_function

import argparse
import ast
from contextlib import contextmanager
from datetime import datetime
import json
import os
from os.path import exists, isdir, isfile
import sys

import attr
from attr.validators import instance_of, optional
from kwonly_args import kwonly_defaults, KWONLY_REQUIRED
import six

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
        if args.java:
            jw = JavaWriter(args.java)
            for cls in classes:
                jw.write(cls)
        elif args.json:
            print(json.dumps(classes, default=lambda c: attr.asdict(c), indent=4))
    except CommandError as e:
        print(e, file=sys.stderr)
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
    for dirname in path:
        mod_filename_prefix = join(dirname, mod_name.replace(".", "/"))
        # Packages take priority over modules (https://stackoverflow.com/questions/4092395/)
        package_filename = join(mod_filename_prefix, "__init__.py")
        if isfile(package_filename):
            return package_filename

        mod_filename = mod_filename_prefix + ".py"
        if isfile(mod_filename):
            return mod_filename

    raise CommandError("Module not found: " + mod_name)


# Only user-supplied fields are validated.
@attr.s
class Class(object):
    name = attr.ib()
    extends = attr.ib(validator=optional(instance_of(str)))
    implements = attr.ib(validator=instance_of((list, tuple)))
    package = attr.ib(validator=instance_of(str))
    modifiers = attr.ib(validator=instance_of(str))
    constructors = attr.ib()
    methods = attr.ib()


# Attrs constructors can't enforce keyword-only arguments, so we use wrapper functions.
@kwonly_defaults
def constructor(arg_types, modifiers="public", throws=None):
    if throws is None:
        throws = []
    return Constructor(arg_types, modifiers, throws)

@attr.s
class Constructor(object):
    arg_types = attr.ib(validator=instance_of((list, tuple)))
    modifiers = attr.ib(validator=instance_of(str))
    throws = attr.ib(validator=instance_of((list, tuple)))


@kwonly_defaults
def Override(return_type, arg_types, modifiers="public", throws=None, name=KWONLY_REQUIRED):
    return method(return_type, arg_types, modifiers=("@Override " + modifiers),
                  throws=throws, name=name)

@kwonly_defaults
def method(return_type, arg_types, modifiers="public", throws=None, name=KWONLY_REQUIRED):
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

        try:
            root = ast.parse(open(self.filename).read(), self.filename)
        except SyntaxError as e:
            raise CommandError("{}:{}:{}: {}".format(e.filename, e.lineno, e.offset, e.msg))

        # These are all the node types which can change global bindings. We map the bound name
        # to its fully-qualified name if it's a usable import, or otherwise to the node which
        # bound it so we can give a useful error if the name is passed to one of our functions.
        for node in root.body:
            if isinstance(node, ast.FunctionDef):
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
            elif isinstance(node, ast.AugAssign):
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

        for base in node.bases:
            if isinstance(base, ast.Call) and self.lookup(base.func) == "java.static_proxy":
                return self.process_static_proxy(node, base)
        return None

    def process_static_proxy(self, cls, sp_call):
        @kwonly_defaults
        def static_proxy(extends, package=None, modifiers="public", *implements):
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
            return Class(cls.name, extends, implements, package, modifiers, constructors, methods)
        except TypeError as e:
            self.error(cls, type_error_msg(e))

    # Calls the given function with the Call node's arguments, which must all be either
    # literals, or expressions which can be turned into strings by resolve(). Additional
    # keyword arguments may also be passed through.
    def call(self, function, call, **kwargs):
        if call.starargs or call.kwargs:
            self.error(call, "*args and **kwargs are not supported here")
        args = [self.evaluate(a) for a in call.args]
        kwargs.update((kw.arg, self.evaluate(kw.value)) for kw in call.keywords)
        try:
            result = function(*args, **kwargs)
        except TypeError as e:
            self.error(call, type_error_msg(e))
        return result

    def evaluate(self, expr):
        if isinstance(expr, ast.Num):
            return expr.n
        elif isinstance(expr, ast.Str):
            return expr.s
        elif isinstance(expr, ast.Name):
            if expr.id in ["True", "False", "None"]:
                return getattr(six.moves.builtins, expr.id)
            else:
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


class JavaWriter(object):
    def __init__(self, root_dirname):
        self.root_dirname = root_dirname

    def write(self, cls):
        pkg_dirname = join(self.root_dirname, cls.package.replace(".", "/"))
        if not isdir(pkg_dirname):
            os.makedirs(pkg_dirname)

        self.indent = 0
        with open(join(pkg_dirname, cls.name + ".java"), "w") as self.out_file:
            self.line("// Generated at {} with the command line:",
                      datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))
            self.line("// {}", " ".join(sys.argv[1:]))
            self.line()
            self.line("package {};", cls.package)
            self.line()
            with self.block("{} class {} {} {}", cls.modifiers, cls.name,
                            self.format_optional("extends", cls.extends),
                            self.format_list("implements", cls.implements)):
                self.line()
                for ctor in cls.constructors:
                    self.constructor(cls, ctor)
                for method in cls.methods:
                    self.method(method)

    def constructor(self, cls, ctor):
        with self.block("{} {}{}", ctor.modifiers, cls.name,
                        self.format_args_throws(ctor)):
            pass
        self.line()

    def method(self, method):
        with self.block("{} {} {}{}", method.modifiers, method.return_type,
                        method.name, self.format_args_throws(method)):
            pass
        self.line()

    def format_args_throws(self, method):
        args = self.format_list("{} arg{}".format(t, i)
                                for i, t in enumerate(method.arg_types))
        throws = self.format_list("throws", method.throws)
        return "({}) {}".format(args, throws)
        self.line()

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


class CommandError(Exception):
    pass


if __name__ == "__main__":
    main()
