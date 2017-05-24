from __future__ import absolute_import, division, print_function

import ctypes
from functools import total_ordering
import six

import chaquopy
from .chaquopy import JavaClass, check_range_char, check_range_float32

__all__ = ["jni_sig", "jni_method_sig",
           "Wrapper", "Primitive", "NumericPrimitive", "IntPrimitive", "FloatPrimitive",
           "jvoid", "jboolean", "jbyte", "jshort", "jint", "jlong", "jfloat", "jdouble",
           "jchar",  "ArrayWrapper", "jarray"]


# These classes wrap a method parameter to specify its Java primitive type.
#
# Java has more primitive types than Python, so where more than one compatible integer or
# floating-point overload is available for a method call, the widest one will be used by
# default. Similarly, where a Python string is passed to a method which has overloads for
# `String` `char` and `char[]`, `String` will be used. If this behavior gives undesired
# results, these wrapper classes can be used to specify a primitive type for the parameter.
#
# For example, if `p` is a `PrintStream`, `p.print(42)` will call `print(long)`, whereas
# `p.print(jint(42))` will call `print(int)`. Likewise, `p.print("x")` will call
# `print(String)`, while `p.print(jchar("x"))` will call `print(char)`.
#
# The numeric type wrappers take an optional `truncate` parameter. If this is true, any excess
# high-order bits of the given value will be discarded, as with a cast in Java. Otherwise,
# passing an out-of-range value will result in an OverflowError.


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


# `Wrapper` subclasses for the 9 primitive types (including `void`), indexed by Java language
# name (e.g. `int`).
primitives = {}

class PrimitiveMeta(type):
    def __init__(cls, cls_name, bases, cls_dict):
        if hasattr(cls, "sig") and len(cls.sig) == 1:
            primitives[cls_name[1:]] = cls

@total_ordering
class Primitive(six.with_metaclass(PrimitiveMeta, Wrapper)):
    def __repr__(self):
        return "{}({})".format(type(self).__name__, self.value)

class jvoid(Primitive):
    sig = "V"

    def __init__(self):
        raise TypeError("Cannot create a jvoid object")


class jboolean(Primitive):
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
    sig = "B"
    truncator = ctypes.c_int8

class jshort(IntPrimitive):
    sig = "S"
    truncator = ctypes.c_int16

class jint(IntPrimitive):
    sig = "I"
    truncator = ctypes.c_int32

class jlong(IntPrimitive):
    sig = "J"
    truncator = ctypes.c_int64


class FloatPrimitive(NumericPrimitive):
    def __init__(self, value, truncate=False):
        if not (isinstance(value, (float, six.integer_types)) and not isinstance(value, bool)):
            raise TypeError("a float is required")
        self.value = float(value)

class jfloat(FloatPrimitive):
    sig = "F"

    def __init__(self, value, truncate=False):
        FloatPrimitive.__init__(self, value)
        self.value = ctypes.c_float(value).value
        if not truncate:
            check_range_float32(value)

class jdouble(FloatPrimitive):
    sig = "D"


class jchar(Primitive):
    sig = "C"

    def __init__(self, value):
        check_range_char(value)
        self.value = six.text_type(value)

    def __repr__(self):
        # repr(self.value) will include a 'u' prefix in Python 2.
        return "{}('{}')".format(type(self).__name__, self.value)


class ArrayWrapper(Wrapper):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return "jarray('{}', {!r})".format(self.sig[1:], self.value)

def jarray(element_type, *args):
    """With one argument, `jarray` returns a wrapper class for an array of the given element type.
    With two arguments, the second argument must be an iterable which is wrapped with the class
    and returned.

    A Python iterable can normally be passed directly to a Java method. But where a method has
    multiple overloads which take an array, the iterable must be wrapped with `jarray` to
    specify the intended type.

    For example, if a class defines the methods `f(long[] x)` and `f(int[] x)`, calling
    `f([1,2,3])` will fail with an ambiguous overload error. To select the `int[]` overload,
    use the syntax `f(jarray(jint, [1,2,3]))` or `f(jarray(jint)([1,2,3]))`.

    The element type may be specified as any of:

    * `jboolean`, `jbyte`, etc.
    * A class returned by the one-argument form of `jarray`
    * A class returned by `autoclass`
    * A java.lang.Class instance
    * A JNI type signature

    Examples::

        int[]       jarray(jint)
        int[][]     jarray(jarray(jint))
        String[]    jarray(autoclass("java.lang.String"))
    """
    element_sig = (element_type if isinstance(element_type, six.string_types)
                   else jni_sig(element_type))
    wrapper = type(str("jarray_" + element_sig),
                   (ArrayWrapper,),
                   {"sig": "[" + element_sig})
    if args:
        value, = args
        return wrapper(value)
    else:
        return wrapper


def jni_method_sig(returns, takes):
    return "(" + "".join(map(jni_sig, takes)) + ")" + jni_sig(returns)

# TODO #5155 don't expose JNI signatures to users
def format_args(args):
    """args is in the same format as JavaMethod.definition_args."""
    return "(" + ", ".join(args) + ")"


def jni_sig(c):
    if isinstance(c, JavaClass):
        return "L" + c.__javaclass__.replace(".", "/") + ";"
    elif isinstance(c, chaquopy.autoclass("java.lang.Class")):
        name = c.getName()
        if name in primitives:
            return primitives[name].sig
        elif name.startswith("["):
            return name.replace(".", "/")
        else:
            return "L" + name.replace(".", "/") + ";"
    elif issubclass(c, Wrapper):
        return c.sig
    raise TypeError("{} object does not specify a Java type".format(type(c).__name__))
