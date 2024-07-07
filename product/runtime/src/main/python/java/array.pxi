from collections.abc import Sequence
import itertools

from cpython cimport Py_buffer
from cpython.buffer cimport (PyBUF_FORMAT, PyBUF_ANY_CONTIGUOUS, PyBUF_ND, PyBuffer_FillInfo,
                             PyBuffer_Release, PyObject_CheckBuffer, PyObject_GetBuffer)
from libc.string cimport memcpy, memset

global_class("java.lang.System")
global_class("java.util.Arrays")


# Map each Java array type to a list of buffer format codes it accepts, and an itemsize. The
# first format in the list is the one we will produce in Java-to-Python conversions.
#
# We only accept formats where a simple memory copy is guaranteed to give the same result as
# assigning one element at a time. The one exception is that to provide an easy and efficient
# way to convert Python bytes or bytearray objects to Java byte[], we allow initializing a
# byte[] from buffer type `B` (uint8). This maps values 128 to 255 to Java values -128 to -1,
# even though those values would give an OverflowError on element assignment.
#
# We could remove this inconsistency by allowing SetByteArrayElement to take values 128 to 255
# as well. But that would just increase the inconsistency between byte and the other integer
# types, and also raise new questions like why can you pass these values to an array element
# but not to a field of the same type. Better to limit this special case to the one thing it's
# intended for.
BUFFER_FORMATS = {
    "Z": ([b"?"], 1),
    "B": ([b"b", b"B"], 1),    # See comment above.
    "S": ([b"h"], 2),
    "I": ([b"i", b"l"], 4),    # C `long` may be 32 or 64-bit.
    "J": ([b"q", b"l"], 8),    #
    "F": ([b"f"], 4),
    "D": ([b"d"], 8),
    # char arrays don't support the buffer protocol. The `array` module mentions a `u` buffer
    # type, but it's deprecated and isn't guaranteed to be 16 bits. And we can't use type `H`
    # (uint16) either, because uint16 and char can't be assigned to each other, which would
    # break the principle of "same result as assigning one element at a time".
}


cpdef jarray(element_type):
    """Returns a Python class for a Java array type. The element type may be specified as any of:

    * The primitive types :any:`jboolean`, :any:`jbyte`, etc.
    * A Java class returned by :any:`jclass`, or by `jarray` itself.
    * A `java.lang.Class` instance
    * A JNI type signature
    """
    element_sig = jni_sig(element_type)
    name = "[" + element_sig
    with class_lock:
        cls = jclass_cache.get(name)
        if not cls:
            base_cls = JavaBufferArray if element_sig in BUFFER_FORMATS else JavaArray
            cls = ArrayClass(None, (base_cls, Cloneable, Serializable, JavaObject),
                             {"_chaquopy_name": name})
            cls._element_sig = element_sig
        return cls


class ArrayClass(JavaClass):
    def __call__(cls, *args, **kwargs):
        self = JavaClass.__call__(cls, *args, **kwargs)
        if "instance" in kwargs:
            (<JavaArray?>self).length = CQPEnv().GetArrayLength(self._chaquopy_this)
        return self


cdef class JavaArray:
    # This must be a cdef member, because __getbuffer__ returns a pointer to it.
    cdef Py_ssize_t length

    def __init__(self, length_or_value):
        if isinstance(length_or_value, int):
            self.length, value = length_or_value, None
        else:
            self.length, value = len(length_or_value), length_or_value

        env = CQPEnv()
        r = self._element_sig[0]
        if r == "Z":
            this = env.NewBooleanArray(self.length)
        elif r == "B":
            this = env.NewByteArray(self.length)
        elif r == "S":
            this = env.NewShortArray(self.length)
        elif r == "I":
            this = env.NewIntArray(self.length)
        elif r == "J":
            this = env.NewLongArray(self.length)
        elif r == "F":
            this = env.NewFloatArray(self.length)
        elif r == "D":
            this = env.NewDoubleArray(self.length)
        elif r == "C":
            this = env.NewCharArray(self.length)
        elif r in "L[":
            this = env.NewObjectArray(self.length, env.FindClass(self._element_sig))
        else:
            raise ValueError(f"Invalid signature '{self._element_sig}'")
        set_this(self, this.global_ref())

        if value is not None:
            self._init_value(env, value)

    def _init_value(self, CQPEnv env, value):
        for i, v in enumerate(value):
            array_set(self, i, v)

    def __repr__(self):
        return f"{type(self).__name__}({format_array(self)})"

    # Override JavaObject.__str__, which calls toString()
    def __str__(self):
        return repr(self)

    def __len__(self):
        return self.length

    def __getitem__(self, key):
        global Arrays
        if isinstance(key, slice):
            r = range(*key.indices(self.length))
            if r.step == 1:
                return Arrays.copyOfRange(self, r.start, max(r.start, r.stop))
            else:
                return type(self)([array_get(self, i) for i in r])
        else:
            return array_get(self, self._int_key(key))

    # `copy` is not part of the Sequence ABC, but the standard types all provide it.
    def copy(self):
        return self[:]

    def __copy__(self):
        return self.copy()

    # TODO: __deepcopy__ (see notes at TestArray.test_copy_module)

    def __setitem__(self, key, value):
        global System
        if isinstance(key, slice):
            r = range(*key.indices(self.length))
            if len(r) != len(value):
                raise ValueError(
                    f"can't set slice of length {len(r)} from value of length {len(value)}")
            if r.step == 1:
                # It's not enough just to test whether `value` is an array, because `arraycopy`
                # can't copy between primitive array types even where the elements could have
                # been assigned one at a time, such as int[] to float[].
                if not isinstance(value, type(self)):
                    value = type(self)(value)
                System.arraycopy(value, 0, self, r.start, len(value))
            else:
                for i, v in zip(r, value):
                    array_set(self, i, v)
        else:
            array_set(self, self._int_key(key), value)

    cdef int _int_key(self, key) except -1:
        try:
            key = key.__index__()
        except AttributeError:
            # Same wording as the built-in list type.
            raise TypeError(f"array indices must be integers or slices, not {type(key).__name__}")
        if key < 0:
            key = self.length + key
        if not (0 <= key < self.length):
            # Same wording as the built-in list type.
            raise IndexError("array index out of range")
        return key

    def __eq__(self, other):
        try:
            return ((self.length == len(other)) and
                    all([s == o for s, o in zip(self, other)]))
        except TypeError:
            # `other` may be an array cast to Object, in which case returning NotImplemented
            # allows JavaObject.__eq__(other, self) to be tried.
            return NotImplemented

    # Like Python lists, jarray objects should be unhashable because they're mutable.
    __hash__ = None

    def __add__(self, other):
        return list(itertools.chain(self, other))
    def __radd__(self, other):
        return list(itertools.chain(other, self))

    # Because JavaArray is a cdef type, it can't inherit the Sequence ABC directly, so we use
    # the `register` API instead below. However, this doesn't give us the mixin methods, so we
    # have to implement them all explicitly.
    #
    # __contains__, __iter__ and __reversed__ are redundant since we have __getitem__ and
    # __len__, but some code still requires them to be present, e.g.
    # https://github.com/pandas-dev/pandas/blob/v1.3.2/pandas/_libs/lib.pyx#L1108
    def __contains__(self, value):
        return Sequence.__contains__(self, value)
    def __iter__(self):
        return Sequence.__iter__(self)
    def __reversed__(self):
        return Sequence.__reversed__(self)
    def index(self, *args, **kwargs):
        return Sequence.index(self, *args, **kwargs)
    def count(self, value):
        return Sequence.count(self, value)

    # Provide a minimal ndarray-style interface for the code at
    # https://github.com/pandas-dev/pandas/blob/v0.25.3/pandas/core/internals/construction.py#L292.
    # As noted at https://github.com/chaquo/chaquopy/issues/306, newer versions of Pandas are
    # more restrictive in what the DataFrame constructor accepts, so this code might not be
    # used anymore, but we'll keep it for backward compatibility.
    @property
    def ndim(self):
        return 1

    @property
    def shape(self):
        return (self.length,)

    def reshape(self, shape):
        import numpy
        return numpy.array(self).reshape(shape)

# We don't register as a MutableSequence because we don't support adding or removing elements.
Sequence.register(JavaArray)


# numpy.array calls __getbuffer__ twice without checking for exceptions in between
# (https://github.com/numpy/numpy/blob/v1.17.4/numpy/core/src/multiarray/ctors.c#L733).
# Unfortunately this means that if __getbuffer__ throws an exception to indicate that the
# buffer interface isn't supported, that exception will still be set on the second call, which
# will cause all kinds of confusion, and probably stop Numpy from falling back on the Python
# sequence protocol. We work around this by having a specialized class for array types which
# support the buffer protocol.
cdef class JavaBufferArray(JavaArray):
    def _init_value(self, CQPEnv env, value):
        cdef Py_buffer buffer
        memset(&buffer, 0, sizeof(buffer))
        try:
            if not PyObject_CheckBuffer(value):
                raise BufferError("object does not support the buffer protocol")
            try:
                PyObject_GetBuffer(value, &buffer, PyBUF_FORMAT|PyBUF_ANY_CONTIGUOUS)
            except ValueError as e:
                # NumPy throws a ValueError when the array is non-contiguous.
                raise BufferError(str(e))

            formats, itemsize = BUFFER_FORMATS[self._element_sig]
            if not (buffer.format in formats and buffer.itemsize == itemsize):
                raise BufferError(f"Java array type {self._element_sig} does not accept "
                                  f"format={buffer.format}, itemsize={buffer.itemsize}")
            if buffer.ndim != 1:
                raise BufferError("object has {buffer.ndim} dimensions, only 1 is supported")
            if buffer.shape[0] != self.length:
                raise BufferError(f"got {buffer.shape[0]} elements, expected {self.length}")
            if buffer.len != self.length * itemsize:
                raise BufferError(f"got {buffer.len} bytes, expected {self.length * itemsize}")
            array_set_elements(self, env, buffer.buf)
        except BufferError:
            # Fall back on assigning one element at a time. Whether this works may depend on
            # both the data type and the values, e.g. uint32 -> double will always work, but
            # uint32 -> int will only work if the value is within range.
            super()._init_value(env, value)
        finally:
            if <PyObject*>buffer.obj != NULL:
                PyBuffer_Release(&buffer)

    def __getbuffer__(self, Py_buffer *buffer, int flags):
        env = CQPEnv()
        elems = array_get_elements(self, env)
        try:
            formats, itemsize = BUFFER_FORMATS[self._element_sig]
            PyBuffer_FillInfo(buffer, self, elems, self.length * itemsize, 0, flags)
            buffer.itemsize = itemsize
            if flags & PyBUF_FORMAT:
                buffer.format = formats[0]
            if flags & PyBUF_ND:
                buffer.shape = &self.length
        except:
            array_release_elements(self, env, elems)
            raise

    def __releasebuffer__(self, Py_buffer *buffer):
        array_release_elements(self, CQPEnv(), buffer.buf)


cdef array_get(self, jint index):
    env = CQPEnv()
    cdef JNIRef this = self._chaquopy_this
    r = self._element_sig[0]
    if r == "Z":
        return env.GetBooleanArrayElement(this, index)
    elif r == "B":
        return env.GetByteArrayElement(this, index)
    elif r == "S":
        return env.GetShortArrayElement(this, index)
    elif r == "I":
        return env.GetIntArrayElement(this, index)
    elif r == "J":
        return env.GetLongArrayElement(this, index)
    elif r == "F":
        return env.GetFloatArrayElement(this, index)
    elif r == "D":
        return env.GetDoubleArrayElement(this, index)
    elif r == "C":
        return env.GetCharArrayElement(this, index)
    elif r in "L[":
        return j2p(env.j_env, env.GetObjectArrayElement(this, index))
    else:
        raise ValueError(f"Invalid signature '{self._element_sig}'")

cdef array_set(self, jint index, value):
    env = CQPEnv()
    cdef JNIRef this = self._chaquopy_this
    # Android's JVM doesn't type-check SetObjectArrayElement calls before API level 16,
    # so we need to check against the actual array type.
    element_sig = object_sig(env, this)[1:]
    value_p2j = p2j(env.j_env, element_sig, value)
    r = element_sig[0]
    if r == "Z":
        env.SetBooleanArrayElement(this, index, value_p2j)
    elif r == "B":
        env.SetByteArrayElement(this, index, value_p2j)
    elif r == "S":
        env.SetShortArrayElement(this, index, value_p2j)
    elif r == "I":
        env.SetIntArrayElement(this, index, value_p2j)
    elif r == "J":
        env.SetLongArrayElement(this, index, value_p2j)
    elif r == "F":
        env.SetFloatArrayElement(this, index, value_p2j)
    elif r == "D":
        env.SetDoubleArrayElement(this, index, value_p2j)
    elif r == "C":
        env.SetCharArrayElement(this, index, value_p2j)
    elif r in "L[":
        env.SetObjectArrayElement(this, index, value_p2j)
    else:
        raise ValueError(f"Invalid signature '{element_sig}'")


cdef void *array_get_elements(self, CQPEnv env) except NULL:
    r = self._element_sig[0]
    if r == "Z":
        return env.GetBooleanArrayElements(self._chaquopy_this)
    elif r == "B":
        return env.GetByteArrayElements(self._chaquopy_this)
    elif r == "S":
        return env.GetShortArrayElements(self._chaquopy_this)
    elif r == "I":
        return env.GetIntArrayElements(self._chaquopy_this)
    elif r == "J":
        return env.GetLongArrayElements(self._chaquopy_this)
    elif r == "F":
        return env.GetFloatArrayElements(self._chaquopy_this)
    elif r == "D":
        return env.GetDoubleArrayElements(self._chaquopy_this)
    elif r == "C":
        return env.GetCharArrayElements(self._chaquopy_this)
    else:
        raise ValueError(f"Invalid signature '{self._element_sig}'")


cdef array_release_elements(self, CQPEnv env, void *elems):
    r = self._element_sig[0]
    if r == "Z":
        env.ReleaseBooleanArrayElements(self._chaquopy_this, <jboolean*>elems, 0)
    elif r == "B":
        env.ReleaseByteArrayElements(self._chaquopy_this, <jbyte*>elems, 0)
    elif r == "S":
        env.ReleaseShortArrayElements(self._chaquopy_this, <jshort*>elems, 0)
    elif r == "I":
        env.ReleaseIntArrayElements(self._chaquopy_this, <jint*>elems, 0)
    elif r == "J":
        env.ReleaseLongArrayElements(self._chaquopy_this, <jlong*>elems, 0)
    elif r == "F":
        env.ReleaseFloatArrayElements(self._chaquopy_this, <jfloat*>elems, 0)
    elif r == "D":
        env.ReleaseDoubleArrayElements(self._chaquopy_this, <jdouble*>elems, 0)
    elif r == "C":
        env.ReleaseCharArrayElements(self._chaquopy_this, <jchar*>elems, 0)
    else:
        raise ValueError(f"Invalid signature '{self._element_sig}'")


cdef array_set_elements(JavaBufferArray self, CQPEnv env, void *elems):
    r = self._element_sig[0]
    if r == "Z":
        env.SetBooleanArrayRegion(self._chaquopy_this, 0, self.length, <jboolean*>elems)
    elif r == "B":
        env.SetByteArrayRegion(self._chaquopy_this, 0, self.length, <jbyte*>elems)
    elif r == "S":
        env.SetShortArrayRegion(self._chaquopy_this, 0, self.length, <jshort*>elems)
    elif r == "I":
        env.SetIntArrayRegion(self._chaquopy_this, 0, self.length, <jint*>elems)
    elif r == "J":
        env.SetLongArrayRegion(self._chaquopy_this, 0, self.length, <jlong*>elems)
    elif r == "F":
        env.SetFloatArrayRegion(self._chaquopy_this, 0, self.length, <jfloat*>elems)
    elif r == "D":
        env.SetDoubleArrayRegion(self._chaquopy_this, 0, self.length, <jdouble*>elems)
    elif r == "C":
        env.SetCharArrayRegion(self._chaquopy_this, 0, self.length, <jchar*>elems)
    else:
        raise ValueError(f"Invalid signature '{self._element_sig}'")


# Formats a possibly-multidimensional array using nested "[]" syntax.
cdef format_array(array):
    return  ("[" +
             ", ".join([format_array(value) if isinstance(value, JavaArray) else repr(value)
                        for value in array]) +
             "]")
