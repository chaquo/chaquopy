"""Copyright (c) 2017 Chaquo Ltd. All rights reserved."""

from __future__ import absolute_import, division, print_function

import ctypes
from functools import total_ordering
from java._vendor import six

import java
from .chaquopy import (JavaArray, JavaClass, NoneCast, check_range_char, check_range_float32,
                       CQPEnv, klass_sig, str_repr)

__all__ = ["jni_sig", "name_to_sig", "jni_method_sig", "split_method_sig",
           "sig_to_java", "args_sig_to_java",
           "primitives_by_name", "primitives_by_sig",
           "Primitive", "NumericPrimitive", "IntPrimitive", "FloatPrimitive",
           "jvoid", "jboolean", "jbyte", "jshort", "jint", "jlong", "jfloat", "jdouble", "jchar"]


primitives_by_name = {}
primitives_by_sig = {}

class PrimitiveMeta(type):
    def __init__(cls, cls_name, bases, cls_dict):
        if hasattr(cls, "name"):
            primitives_by_name[cls.name] = cls
            primitives_by_sig[cls.sig] = cls

@total_ordering
class Primitive(six.with_metaclass(PrimitiveMeta, object)):
    def __repr__(self):
        return "{}({})".format(type(self).__name__, self.value)

    def __eq__(self, other):
        if isinstance(other, Primitive):
            return self.value == other.value
        else:
            return self.value == other

    def __hash__(self):
        return hash(self.value)

    def __lt__(self, other):
        if isinstance(other, Primitive):
            return self.value < other.value
        else:
            return self.value < other


class jvoid(Primitive):
    """`jvoid` cannot be instantiated, but may be used as a return type when defining a
    :ref:`static proxy <static-proxy>`.
    """
    name = "void"
    sig = "V"

    def __init__(self):
        raise TypeError("Cannot create a jvoid object")


class jboolean(Primitive):
    name = "boolean"
    sig = "Z"

    def __init__(self, value):
        self.value = bool(value)


class NumericPrimitive(Primitive):
    pass


class IntPrimitive(NumericPrimitive):
    def __init__(self, value, truncate=False):
        if not (isinstance(value, six.integer_types) and not isinstance(value, bool)):
            raise TypeError("an integer is required")
        self.value = self.truncator(value).value
        if not truncate and self.value != value:
            raise OverflowError("value too large to convert to " + type(self).__name__)

class jbyte(IntPrimitive):
    name = "byte"
    sig = "B"
    truncator = ctypes.c_int8

class jshort(IntPrimitive):
    name = "short"
    sig = "S"
    truncator = ctypes.c_int16

class jint(IntPrimitive):
    name = "int"
    sig = "I"
    truncator = ctypes.c_int32

class jlong(IntPrimitive):
    name = "long"
    sig = "J"
    truncator = ctypes.c_int64


class FloatPrimitive(NumericPrimitive):
    def __init__(self, value, truncate=False):
        if not (isinstance(value, (float, six.integer_types)) and not isinstance(value, bool)):
            raise TypeError("a float is required")
        self.value = float(value)

class jfloat(FloatPrimitive):
    name = "float"
    sig = "F"

    def __init__(self, value, truncate=False):
        FloatPrimitive.__init__(self, value)
        self.value = ctypes.c_float(value).value
        if not truncate:
            check_range_float32(value)

class jdouble(FloatPrimitive):
    name = "double"
    sig = "D"


class jchar(Primitive):
    name = "char"
    sig = "C"

    def __init__(self, value):
        check_range_char(value)
        self.value = six.text_type(value)

    def __repr__(self):
        return "{}({})".format(type(self).__name__, str_repr(self.value))


def jni_method_sig(returns, takes):
    return "(" + "".join(map(jni_sig, takes)) + ")" + jni_sig(returns)


def jni_sig(c):
    if isinstance(c, six.string_types):
        sig_to_java(c)  # Check syntax
        return c.replace(".", "/")
    elif isinstance(c, type):
        if isinstance(c, JavaClass):
            if issubclass(c, JavaArray):
                return c.__name__
            else:
                return klass_sig(CQPEnv(), c._chaquopy_j_klass)
        elif issubclass(c, (NoneCast, Primitive)):
            return c.sig
    elif isinstance(c, java.jclass("java.lang.Class")):
        return name_to_sig(c.getName())
    else:
        raise TypeError("{} object does not specify a Java type".format(type(c).__name__))


# `name` is in the format returned by Class.getName()
def name_to_sig(name):
    if name in primitives_by_name:
        return primitives_by_name[name].sig
    elif name.startswith("["):
        return name.replace(".", "/")
    else:
        return "L" + name.replace(".", "/") + ";"


def split_method_sig(definition):
    assert definition.startswith("(")
    argdef, ret = definition[1:].split(')')
    args = []

    while len(argdef):
        prefix = ''
        c = argdef[0]
        while c == '[':
            prefix += c
            argdef = argdef[1:]
            c = argdef[0]
        if c in 'ZBCSIJFD':
            args.append(prefix + c)
            argdef = argdef[1:]
            continue
        if c == 'L':
            c, argdef = argdef.split(';', 1)
            args.append(prefix + c + ';')
            continue
        raise ValueError("Invalid type code '{}' in definition '{}'".format(c, definition))

    return ret, tuple(args)


def sig_to_java(sig):
    if sig in primitives_by_sig:
        return primitives_by_sig[sig].name
    if sig.startswith("["):
        return sig_to_java(sig[1:]) + "[]"
    if sig.startswith("L") and sig.endswith(";"):
        return sig[1:-1].replace("/", ".")
    raise ValueError("Invalid definition: '{}'".format(sig))


# `split_args_sig` is in the format of the args tuple returned by split_method_sig.
def args_sig_to_java(split_args_sig, varargs=False):
    formatted_args = []
    for i, sig in enumerate(split_args_sig):
        if varargs and i == (len(split_args_sig) - 1):
            assert sig.startswith("[")
            formatted_args.append(sig_to_java(sig[1:]) + "...")
        else:
            formatted_args.append(sig_to_java(sig))
    return "(" + ", ".join(formatted_args) + ")"
