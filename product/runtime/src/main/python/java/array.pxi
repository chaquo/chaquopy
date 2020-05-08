import itertools

from cpython cimport Py_buffer
from cpython.buffer cimport PyBuffer_FillInfo


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
        return cls


class ArrayClass(JavaClass):
    def __call__(cls, *args, **kwargs):
        self = JavaClass.__call__(cls, *args, **kwargs)
        self._chaquopy_len = CQPEnv().GetArrayLength(self._chaquopy_this)
        return self


cdef class JavaArray(object):
    def __init__(self, length_or_value):
        if isinstance(length_or_value, int):
            length, value = length_or_value, None
        else:
            length, value = len(length_or_value), length_or_value

        env = CQPEnv()
        element_sig = type(self).__name__[1:]
        r = element_sig[0]
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
            this = env.NewObjectArray(length, env.FindClass(element_sig))
        else:
            raise ValueError(f"Invalid signature '{element_sig}'")
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
        return f"jarray('{type(self).__name__[1:]}')({format_array(self)})"

    # Override JavaObject.__str__, which calls toString()
    def __str__(self):
        return repr(self)

    # We currently support calling bytes() and bytearray() on byte[] arrays only. For Java's
    # other integer types, there are two possible behaviors:
    #   * Require the elements to have values 0-255, and return one byte per element.
    #   * Return the elements as stored in memory, e.g. 2 bytes per short[] element.
    #
    # In future, when we implement the buffer protocol for other primitive array types to
    # support NumPy (TODO #5464), we'll automatically get the in-memory behavior. The only way
    # to stop this would be to implement __bytes__, but that would have no effect on
    # bytearray(). So we'll have to accept it, and if the user wants the byte-per-element
    # behavior, they can just call bytes(list(a)).
    def __getbuffer__(self, Py_buffer *buffer, int flags):
        signature = type(self).__name__
        if signature != "[B":
            raise TypeError(f"__getbuffer__ is not implemented for {sig_to_java(signature)}")

        env = CQPEnv()
        elems = env.GetByteArrayElements(self._chaquopy_this)
        try:
            # This does a signed-to-unsigned conversion: Java values -128 to -1 will be mapped
            # to Python values 128 to 255.
            PyBuffer_FillInfo(buffer, self, elems, self._chaquopy_len, 1, flags)
        except:
            env.ReleaseByteArrayElements(self._chaquopy_this, elems, JNI_ABORT)
            raise
        buffer.internal = elems

    def __releasebuffer__(self, Py_buffer *buffer):
        CQPEnv().ReleaseByteArrayElements(self._chaquopy_this, <jbyte*>buffer.internal, JNI_ABORT)

    def __len__(self):
        return self._chaquopy_len

    def __getitem__(self, key):
        if isinstance(key, int):
            if not (0 <= key < self._chaquopy_len):
                raise IndexError(str(key))
            return array_get(self, key)
        elif isinstance(key, slice):
            # TODO #5192 disabled until tested
            raise TypeError("jarray does not support slice syntax")
            # return [self[i] for i in range(key.indices(self._chaquopy_len))]
        else:
            raise TypeError(f"list indices must be integers or slices, not {type(key).__name__}")

    def __setitem__(self, key, value):
        if isinstance(key, int):
            if not (0 <= key < self._chaquopy_len):
                raise IndexError(str(key))
            array_set(self, key, value)
        elif isinstance(key, slice):
            # TODO #5192 disabled until tested
            raise TypeError("jarray does not support slice syntax")
            # indices = range(key.indices(self._chaquopy_len))
            # if len(indices) != len(value):
            #     raise IndexError(f"Can't set slice of length {len(indices)} "
            #                      f"from value of length {len(value)}")
            # for i, v in zip(indices, value):
            #     self[i] = v
        else:
            raise TypeError(f"list indices must be integers or slices, not {type(key).__name__}")

    def __eq__(self, other):
        try:
            return ((self._chaquopy_len == len(other)) and
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
    element_sig = type(self).__name__[1:]
    r = element_sig[0]
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
        raise ValueError(f"Invalid signature '{element_sig}'")

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


# Formats a possibly-multidimensional array using nested "[]" syntax.
cdef format_array(array):
    return  ("[" +
             ", ".join([format_array(value) if isinstance(value, JavaArray) else repr(value)
                        for value in array]) +
             "]")
