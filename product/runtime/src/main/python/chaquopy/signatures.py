from __future__ import absolute_import, division, print_function

import ctypes
import six

import chaquopy
from .chaquopy import JavaClass, check_range_char, check_range_float32

__all__ = ["jni_sig", "jni_method_sig",
           "Primitive", "NumericPrimitive", "IntPrimitive", "FloatPrimitive",
           "jvoid", "jboolean", "jbyte", "jshort", "jint", "jlong", "jfloat", "jdouble",
           "jchar", "jarray"]


# These functions wrap a method parameter to specify its Java primitive type.
#
# Java has more primitive types than Python, so where more than one compatible integer or
# floating-point overload is available for a method call, the widest one will be used by
# default. Similarly, where an overload is available for both `String` and `char`, `String`
# will be used. If this behavior gives undesired results, these functions can be used to
# choose a specific primitive type for the parameter.
#
# For example, if `p` is a `PrintStream`, `p.print(42)` will call `print(long)`, whereas
# `p.print(jint(42))` will call `print(int)`. Likewise, `p.print("x")` will call
# `print(String)`, while `p.print(jchar("x"))` will call `print(char)`.
#
# The numeric type functions take an optional `truncate` parameter. If this is true, any excess
# high-order bits of the given value will be discarded, as with a Java cast. Otherwise, an
# out-of-range value will result in an OverflowError.
#
# The object types returned by these functions are not specified, but are guaranteed to be
# accepted by compatible Java method calls and field assignments.


# `Wrapper` subclasses for the 9 primitive types (including `void`), indexed by Java language
# name (e.g. `int`).
primitives = {}

class Wrapper(object):
    pass


class PrimitiveMeta(type):
    def __init__(cls, cls_name, bases, cls_dict):
        if hasattr(cls, "sig") and len(cls.sig) == 1:
            primitives[cls_name[1:]] = cls

class Primitive(six.with_metaclass(PrimitiveMeta, Wrapper)):
    pass

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
        self.value = self.truncator(value).value
        if not truncate and self.value != value:
            raise OverflowError("value too large to convert to " + cls.__name__)

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
    pass

class jfloat(FloatPrimitive):
    sig = "F"
    def __init__(self, value, truncate=False):
        if not truncate:
            check_range_float32(value)
        self.value = value

class jdouble(FloatPrimitive):
    sig = "D"
    def __init__(self, value, truncate=False):  # truncate is ignored, but included for consistency.
        self.value = value

class jchar(Primitive):
    sig = "C"
    def __init__(self, value):
        check_range_char(value)
        self.value = value

class ArrayWrapper(Wrapper):
    def __init__(self, value):
        self.value = value

def jarray(element_type, *args):
    """With one argument, returns a wrapper class for an array of the given element type. With two
    arguments, the second argument must be an iterable which is wrapped and returned.

    A Python iterable can normally be passed directly to a Java field or method taking an
    array. But where a method has multiple overloads taking an array, the iterable must be
    wrapped with `jarray` to indicate the intended type.

    For example, if a class defines the methods `f(long[] x)` and `f(int[] x)`, the `int[]`
    overload can be selected using the syntax `f(jarray(jint, [1,2,3]))` or
    `f(jarray(jint)([1,2,3]))`.

    The element type may be specified as:

    * A class returned by `autoclass`
    * A java.lang.Class instance
    * `jboolean`, `jbyte`, etc.
    * A class returned by the one-argument form of `jarray`

    Examples::

        int[]       jarray(jint)
        int[][]     jarray(jarray(jint))
        String[]    jarray(autoclass("java.lang.String"))
    """
    element_sig = jni_sig(element_type)
    wrapper = type("jarray_" + element_sig,
                   (ArrayWrapper,),
                   {"sig": "[" + element_sig})
    if args:
        (value,) = args
        return wrapper(args)
    else:
        return wrapper


def jni_method_sig(returns, takes):
    return "(" + "".join(map(jni_sig, takes)) + ")" + jni_sig(returns)


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
    raise TypeError("Can't produce signature from {} object".format(type(c).__name__))
