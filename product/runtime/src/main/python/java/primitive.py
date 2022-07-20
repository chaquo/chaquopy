import ctypes
from functools import total_ordering

from . import chaquopy

__all__ = ["primitives_by_name", "primitives_by_sig",
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
class Primitive(metaclass=PrimitiveMeta):
    def __repr__(self):
        return f"{type(self).__name__}({self.value!r})"

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
        if not (isinstance(value, int) and not isinstance(value, bool)):
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
        if not (isinstance(value, (float, int)) and not isinstance(value, bool)):
            raise TypeError("a float or integer is required")
        self.value = float(value)

class jfloat(FloatPrimitive):
    name = "float"
    sig = "F"

    def __init__(self, value, truncate=False):
        FloatPrimitive.__init__(self, value)
        self.value = ctypes.c_float(value).value
        if not truncate:
            chaquopy.check_range_float32(value)

class jdouble(FloatPrimitive):
    name = "double"
    sig = "D"


class jchar(Primitive):
    name = "char"
    sig = "C"

    def __init__(self, value):
        chaquopy.check_range_char(value)
        self.value = value
