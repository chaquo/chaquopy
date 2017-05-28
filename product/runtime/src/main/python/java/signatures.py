from __future__ import absolute_import, division, print_function

import ctypes
from functools import total_ordering
import six

import java
from .chaquopy import JavaArray, JavaClass, check_range_char, check_range_float32

__all__ = ["jni_sig", "jni_method_sig", "sig_to_java", "primitives_by_name", "primitives_by_sig",
           "Wrapper", "Primitive", "NumericPrimitive", "IntPrimitive", "FloatPrimitive",
           "jvoid", "jboolean", "jbyte", "jshort", "jint", "jlong", "jfloat", "jdouble", "jchar",
           "jarray"]


class Wrapper(object):
    def __eq__(self, other):
        if isinstance(other, Primitive):
            return self.value == other.value
        else:
            return self.value == other

    def __lt__(self, other):
        if isinstance(other, Primitive):
            return self.value < other.value
        else:
            return self.value < other

    def __hash__(self):
        return hash(self.value)


primitives_by_name = {}
primitives_by_sig = {}

class PrimitiveMeta(type):
    def __init__(cls, cls_name, bases, cls_dict):
        if hasattr(cls, "name"):
            primitives_by_name[cls.name] = cls
            primitives_by_sig[cls.sig] = cls

@total_ordering
class Primitive(six.with_metaclass(PrimitiveMeta, Wrapper)):
    def __repr__(self):
        return "{}({})".format(type(self).__name__, self.value)

class jvoid(Primitive):
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
    """These classes wrap a method parameter to specify its Java primitive type.

    A Python boolean, integer, float or string can normally be used directly as a parameter of
    a Java method. Java has more primitive types than Python, so when more than one compatible
    integer or floating-point overload is applicable for a method call, the longest one will be
    used. Similarly, when a Python string is passed to a method which has overloads for both
    `String` and `char`, the `String` overload will be used. If these rules do not give the
    desired result, the wrapper classes can be used to be more specific about the intended
    type.

    For example, if `p` is a `PrintStream
    <https://docs.oracle.com/javase/7/docs/api/java/io/PrintStream.html>`_::

        p.print(42)              # will call print(long)
        p.print(jint(42))        # will call print(int)
        p.print(42.0)            # will call print(double)
        p.print(jfloat(42.0))    # will call print(float)
        p.print("x")             # will call print(String)
        p.print(jchar("x"))      # will call print(char)

    The numeric type wrappers take an optional `truncate` parameter. If this is set, any excess
    high-order bits of the given value will be discarded, as with a cast in Java. Otherwise,
    passing an out-of-range value will result in an `OverflowError`.

    .. note:: When these wrappers are used, Java overload resolution rules will be in effect
              for the wrapped parameter. For example, a `jint` will only be applicable to a
              Java `int` or larger, and the *shortest* applicable overload will be used.
    """
    name = "char"
    sig = "C"

    def __init__(self, value):
        check_range_char(value)
        self.value = six.text_type(value)

    def __repr__(self):
        # Remove 'u' prefix in Python 2 so tests are consistent.
        return "{}('{}')".format(type(self).__name__, self.value)


class jarray_dict(dict):
    # Use a different subclass for each element type, so overload resolution can be cached.
    def __missing__(self, element_sig):
        subclass = type(str("jarray_" + element_sig),
                        (JavaArray,),
                        {"sig": "[" + element_sig})
        self[element_sig] = subclass
        return subclass

jarray_types = jarray_dict()


def jarray(element_type):
    """Returns a proxy class for a Java array type. Objects of this class implement the Python
    sequence protocol, so they can be read and modified using `[]` syntax.

    Any Python iterable (except a string) can normally be used directly as an array parameter
    of a Java method. But where the method has multiple equally-specific overloads, the value
    must be converted to a `jarray` type to disambiguate the call.

    For example, if a class defines the methods `f(long[] x)` and `f(int[] x)`, calling
    `f([1,2,3])` will fail with an ambiguous overload error. To call the `int[]` overload, use
    `f(jarray(jint)([1,2,3]))`.

    The element type may be specified as any of:

    * The primitive types :any:`jboolean`, :any:`jbyte`, etc.
    * A proxy class returned by :any:`jclass`, or by `jarray` itself.
    * A `java.lang.Class` instance
    * A JNI type signature

    Examples::

        # Python code                           # Java equivalent
        jarray(jint)                            # int[]
        jarray(jarray(jint))                    # int[][]
        jarray(jclass("java.lang.String"))      # String[]
        jarray(jchar)("hello")                  # new char[] {'h', 'e', 'l', 'l', 'o'}
        jarray(jint)(None)                      # (int[])null
    """
    return jarray_types[jni_sig(element_type)]


def jni_method_sig(returns, takes):
    return "(" + "".join(map(jni_sig, takes)) + ")" + jni_sig(returns)


def jni_sig(c):
    if isinstance(c, six.string_types):
        sig_to_java(c)  # Check syntax
        return c
    elif isinstance(c, type):
        if isinstance(c, JavaClass):
            return "L" + c.__javaclass__.replace(".", "/") + ";"
        elif issubclass(c, (Wrapper, JavaArray)):
            return c.sig
    elif isinstance(c, java.jclass("java.lang.Class")):
        name = c.getName()
        if name in primitives_by_name:
            return primitives_by_name[name].sig
        elif name.startswith("["):
            return name.replace(".", "/")
        else:
            return "L" + name.replace(".", "/") + ";"
    raise TypeError("{} object does not specify a Java type".format(type(c).__name__))


def sig_to_java(sig):
    if sig in primitives_by_sig:
        return primitives_by_sig[sig].name
    if sig.startswith("["):
        return sig_to_java(sig[1:]) + "[]"
    if sig.startswith("L") and sig.endswith(";"):
        return sig[1:-1].replace("/", ".")
    raise ValueError("Invalid definition: '{}'".format(sig))
