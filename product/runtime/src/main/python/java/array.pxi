import itertools

from cpython cimport Py_buffer
from cpython.buffer cimport PyBUF_FORMAT, PyBUF_ND, PyBuffer_FillInfo


BUFFER_FORMATS = {
    "B": (b"b", 1),   # byte
    "S": (b"h", 2),   # short
    "I": (b"i", 4),   # int
    "J": (b"q", 8),   # long
    "F": (b"f", 4),   # float
    "D": (b"d", 8),   # double
}


cpdef jarray(element_type):
    """Returns a Python class for a Java array type. The element type may be specified as any of:

    * The primitive types :any:`jboolean`, :any:`jbyte`, etc.
    * A Java class returned by :any:`jclass`, or by `jarray` itself.
    * A `java.lang.Class` instance
    * A JNI type signature
    """
    element_sig = jni_sig(element_type)
    if not isinstance(element_sig, str):
        element_sig = str(element_sig)
    name = "[" + element_sig

    with class_lock:
        cls = jclass_cache.get(name)
        if not cls:
            cls = ArrayClass(None, (JavaArray, Cloneable, Serializable, JavaObject),
                             {"_chaquopy_name": name})
            cls._element_sig = element_sig
        return cls


class ArrayClass(JavaClass):
    def __call__(cls, *args, **kwargs):
        self = JavaClass.__call__(cls, *args, **kwargs)
        (<JavaArray?>self).length = CQPEnv().GetArrayLength(self._chaquopy_this)
        return self


cdef class JavaArray(object):
    cdef Py_ssize_t length

    def __init__(self, length_or_value):
        if isinstance(length_or_value, int):
            length, value = length_or_value, None
        else:
            length, value = len(length_or_value), length_or_value

        env = CQPEnv()
        r = self._element_sig[0]
        if r == "Z":
            this = env.NewBooleanArray(length)
        elif r == "B":
            this = env.NewByteArray(length)
        elif r == "S":
            this = env.NewShortArray(length)
        elif r == "I":
            this = env.NewIntArray(length)
        elif r == "J":
            this = env.NewLongArray(length)
        elif r == "F":
            this = env.NewFloatArray(length)
        elif r == "D":
            this = env.NewDoubleArray(length)
        elif r == "C":
            this = env.NewCharArray(length)
        elif r in "L[":
            this = env.NewObjectArray(length, env.FindClass(self._element_sig))
        else:
            raise ValueError(f"Invalid signature '{self._element_sig}'")
        set_this(self, this.global_ref())

        cdef const uint8_t[:] bytes_view
        if value is not None and length > 0:
            if r == "B":
                try:
                    bytes_view = value
                except Exception:
                    pass
                else:
                    # This does an unsigned-to-signed conversion: Python values 128 to 255 will
                    # be mapped to Java values -128 to -1.
                    env.SetByteArrayRegion(self._chaquopy_this, 0, length,
                                           <jbyte*>&bytes_view[0])
                    return

            for i, v in enumerate(value):
                array_set(self, i, v)

    def __repr__(self):
        return f"{type(self).__name__}({format_array(self)})"

    # Override JavaObject.__str__, which calls toString()
    def __str__(self):
        return repr(self)

    def __getbuffer__(self, Py_buffer *buffer, int flags):
        env = CQPEnv()
        elems = array_get_elements(self, env)
        try:
            format, itemsize = BUFFER_FORMATS[self._element_sig]
            PyBuffer_FillInfo(buffer, self, elems, self.length * itemsize, 0, flags)
            buffer.itemsize = itemsize
            if flags & PyBUF_FORMAT:
                buffer.format = format
            if flags & PyBUF_ND:
                buffer.shape = &self.length
        except:
            array_release_elements(self, env, elems)
            raise

    def __releasebuffer__(self, Py_buffer *buffer):
        array_release_elements(self, CQPEnv(), buffer.buf)

    def __len__(self):
        return self.length

    def __getitem__(self, key):
        if isinstance(key, int):
            if not (0 <= key < self.length):
                raise IndexError(str(key))
            return array_get(self, key)
        elif isinstance(key, slice):
            # TODO #5192 disabled until tested
            raise TypeError("jarray does not support slice syntax")
            # return [self[i] for i in range(key.indices(self.length))]
        else:
            raise TypeError(f"list indices must be integers or slices, not {type(key).__name__}")

    def __setitem__(self, key, value):
        if isinstance(key, int):
            if not (0 <= key < self.length):
                raise IndexError(str(key))
            array_set(self, key, value)
        elif isinstance(key, slice):
            # TODO #5192 disabled until tested
            raise TypeError("jarray does not support slice syntax")
            # indices = range(key.indices(self.length))
            # if len(indices) != len(value):
            #     raise IndexError(f"Can't set slice of length {len(indices)} "
            #                      f"from value of length {len(value)}")
            # for i, v in zip(indices, value):
            #     self[i] = v
        else:
            raise TypeError(f"list indices must be integers or slices, not {type(key).__name__}")

    def __eq__(self, other):
        try:
            return ((self.length == len(other)) and
                    all([s == o for s, o in zip(self, other)]))
        except TypeError:
            # `other` may be an array cast to Object, in which case returning NotImplemented
            # allows JavaObject.__eq__(other, self) to be tried.
            return NotImplemented

    def __ne__(self, other):  # Not automatic in Python 2
        eq = (self == other)
        return eq if (eq is NotImplemented) else (not eq)

    # Like Python lists, jarray objects should be unhashable because they're mutable.
    __hash__ = None

    def __add__(self, other):
        return list(itertools.chain(self, other))
    def __radd__(self, other):
        return list(itertools.chain(other, self))

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
    # We need to type-check against the actual array type, because old versions of Android
    # won't do it for us (#5209).
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
    if r == "B":
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
    else:
        raise TypeError(f"buffer protocol is not implemented for "
                        f"{sig_to_java(self._element_sig)}[]")


cdef array_release_elements(self, CQPEnv env, void *elems):
    r = self._element_sig[0]
    if r == "B":
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
    else:
        raise ValueError(f"Invalid signature '{self._element_sig}'")


# Formats a possibly-multidimensional array using nested "[]" syntax.
cdef format_array(array):
    return  ("[" +
             ", ".join([format_array(value) if isinstance(value, JavaArray) else repr(value)
                        for value in array]) +
             "]")
