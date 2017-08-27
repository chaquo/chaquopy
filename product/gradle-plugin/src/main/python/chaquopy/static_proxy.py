#!/usr/bin/env python

"""Copyright (c) 2017 Chaquo Ltd. All rights reserved."""

from __future__ import absolute_import, division, print_function

import argparse
import ast
import json
import os
from os.path import exists, isdir, isfile
import sys

import attr
from kwonly_args import kwonly_defaults
import six

# Consistent output for tests
def join(*paths):
    return os.path.join(*paths).replace("\\", "/")


PRIMITIVES = ["void", "boolean", "byte", "short", "int", "long", "float", "double", "char"]
JAVA_ALL = (["static_proxy", "jarray"] +    # No point including names not used by this script.
            [("j" + p) for p in PRIMITIVES])
PRIMITIVE_PREFIX = "java.j"


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
            write_java(classes, args.out)
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


Class = attr.make_class("Class", ["name", "package", "extends", "implements",
                                  "constructors", "methods"])
Method = attr.make_class("Method", ["name", "return_type", "arg_types", "modifiers", "throws"])
Constructor = attr.make_class("Constructor", ["arg_types", "modifiers", "throws"])


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

        # These are all the node types which can bind names. We map the bound name to its
        # fully-qualified name if it's a usable import, or otherwise to the node which bound
        # it so we can give a useful error if the name is passed to one of our functions.
        for node in root.body:
            if isinstance(node, ast.FunctionDef):
                self.bindings[node.name] = node
            elif isinstance(node, ast.ClassDef):
                c = self.process_class(node)
                if c:
                    classes.append(c)
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    self.process_assign(t)
            elif isinstance(node, ast.AugAssign):
                self.process_assign(node.target)
            elif isinstance(node, ast.Import):
                self.process_import(node.names, lambda name: name)
            elif isinstance(node, ast.ImportFrom):
                names = node.names
                if node.module == "java" and names[0].name == "*":
                    names = [ast.alias(name, None) for name in JAVA_ALL]

                if node.module and not node.level:  # Absolute import
                    self.process_import(names, lambda name: node.module + "." + name)
                else:                               # Relative import, not supported.
                    self.process_import(names, lambda name: node)

        if not classes:
            self.error(None, "No static_proxy classes found in '{}'. Classes must be defined "
                       "unconditionally at the module top-level.".format(self.filename))
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
            if alias.name != "*":
                self.bindings[alias.asname or alias.name] = get_binding(alias.name)

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
        def static_proxy(extends, package=None, *implements):
            if package is None:
                package = self.name
            return extends, implements, package

        @kwonly_defaults
        def constructor(arg_types, modifiers="public", throws=None):
            return arg_types, modifiers, throws

        @kwonly_defaults
        def Override(return_type, arg_types, modifiers="public", throws=None):
            return return_type, arg_types, "@Override " + modifiers, throws

        extends, implements, package = self.call(static_proxy, sp_call)

        constructors = []
        methods = []
        for stmt in cls.body:
            if isinstance(stmt, ast.FunctionDef):
                for decor in stmt.decorator_list:
                    if isinstance(decor, ast.Call):
                        func = self.lookup(decor.func)
                        if func == "java.constructor":
                            if stmt.name != "__init__":
                                self.error(stmt, "@constructor can only be used on __init__")
                            constructors.append(Constructor(*self.call(constructor, decor)))
                        elif func == "java.Override":
                            if stmt.name == "__init__":
                                self.error(stmt, "@Override cannot be used on __init__")
                            methods.append(Method(stmt.name, *self.call(Override, decor)))

        return Class(cls.name, package, extends, implements, constructors, methods)

    # Calls the given function with the given Call node's arguments, which must all be either
    # literals, or expressions which can be turned into strings by resolve().
    def call(self, function, call):
        if call.starargs or call.kwargs:
            self.error(call, "*args and **kwargs are not supported here")
        args = [self.evaluate(a) for a in call.args]
        kwargs = {kw.arg: self.evaluate(kw.value) for kw in call.keywords}
        try:
            result = function(*args, **kwargs)
        except TypeError as e:
            self.error(call, str(e))
        return result

    def evaluate(self, expr):
        if isinstance(expr, ast.Num):
            return expr.n
        elif isinstance(expr, ast.Str):
            return expr.s
        elif isinstance(expr, ast.Attribute):
            return self.resolve(expr)
        elif isinstance(expr, ast.Name):
            if expr.id in ["True", "False", "None"]:
                return getattr(six.moves.builtins, expr.id)
            else:
                return self.resolve(expr)
        elif isinstance(expr, (ast.List, ast.Tuple)):
            return [self.evaluate(e) for e in expr.elts]
        # The only other literal nodes are Dict and Set, which are not currently required.
        else:
            self.error(expr, type(expr).__name__ + " expression is not supported here")

    def lookup(self, expr):
        try:
            return self.resolve(expr)
        except CommandError:
            return None

    # Converts an expression node to a fully-qualified name or Java type string.
    def resolve(self, expr):
        error = ""
        if isinstance(expr, ast.Attribute):
            return self.resolve(expr.value) + "." + expr.attr.id
        elif isinstance(expr, ast.Name):
            result = self.bindings.get(expr.id)
            if isinstance(result, str):
                if result.startswith(PRIMITIVE_PREFIX):
                    primitive = result[len(PRIMITIVE_PREFIX):]
                    if primitive in PRIMITIVES:
                        result = primitive
                return result
            else:
                error = " '{}'".format(expr.id)
                if isinstance(result, ast.stmt):
                    error += " (bound at {})".format(self.where(result))
                else:
                    error += " (binding not found)"
        elif isinstance(expr, ast.Call) and self.lookup(expr.func) == "java.jarray":
            def jarray(element_type):
                return element_type
            return self.call(jarray, expr) + "[]"

        self.error(expr, "cannot resolve{}. Types must be imported unconditionally "
                   "at the module top-level.".format(error))

    def error(self, node, message):
        if node:
            message = self.where(node) + ": " + message
        raise CommandError(message)

    def where(self, node):
        return "{}:{}:{}".format(self.filename, node.lineno, node.col_offset)


def write_java(classes, out_dir):
    FIXME


class CommandError(Exception):
    pass


if __name__ == "__main__":
    main()

# FIXME test:
# jarray type, including multi-dimensional
# jvoid type
# nested class expression
