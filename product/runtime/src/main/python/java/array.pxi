import collections
import itertools


def jarray(element_type):
    """Returns a Python class for a Java array type. The element type may be specified as any of:

    * The primitive types :any:`jboolean`, :any:`jbyte`, etc.
    * A Java class returned by :any:`jclass`, or by `jarray` itself.
    * A `java.lang.Class` instance
    * A JNI type signature
    """
    element_sig = java.jni_sig(element_type)
    if not isinstance(element_sig, str):
        element_sig = str(element_sig)
    name = "[" + element_sig

    with class_lock:
        cls = jclass_cache.get(name)
        if not cls:
            cls = jclass_proxy(name, [JavaArray, Cloneable, Serializable, JavaObject])
        return cls


class JavaArray(object):
    def __init__(self, value):
        env = CQPEnv()
        cdef JNIRef this
        length = len(value)
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
        for i, v in enumerate(value):
            self[i] = v

    def __repr__(self):
        return f"jarray('{type(self).__name__[1:]}')({format_array(self)})"

    # Override JavaObject.__str__, which calls toString()
    def __str__(self):
        return repr(self)

    def __len__(self):
        return CQPEnv().GetArrayLength(self._chaquopy_this)

    def __getitem__(self, key):
        if isinstance(key, six.integer_types):
            if not (0 <= key < len(self)):
                raise IndexError(str(key))
            return self._chaquopy_get(key)
        elif isinstance(key, slice):
            # TODO #5192 disabled until tested
            raise TypeError("jarray does not support slice syntax")
            # return [self[i] for i in range(key.indices(len(self)))]
        else:
            raise TypeError(f"{type(key).__name__} object is not a valid index")

    def __setitem__(self, key, value):
        if isinstance(key, six.integer_types):
            if not (0 <= key < len(self)):
                raise IndexError(str(key))
            return self._chaquopy_set(key, value)
        elif isinstance(key, slice):
            # TODO #5192 disabled until tested
            raise TypeError("jarray does not support slice syntax")
            # indices = range(key.indices(len(self)))
            # if len(indices) != len(value):
            #     raise IndexError(f"Can't set slice of length {len(indices)} "
            #                      f"from value of length {len(value)}")
            # for i, v in six.moves.zip(indices, value):
            #     self[i] = v
        else:
            raise TypeError(f"{type(key).__name__} object is not a valid index")

    def __eq__(self, other):
        try:
            return ((len(self) == len(other)) and
                    all([s == o for s, o in six.moves.zip(self, other)]))
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

    def _chaquopy_get(self, index):
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

    def _chaquopy_set(self, index, value):
        env = CQPEnv()
        cdef JNIRef this = self._chaquopy_this
        # TODO #5209 use actual rather than declared signature: old Android versions don't
        # type-check correctly.
        element_sig = type(self).__name__[1:]
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
def format_array(array):
    return  ("[" +
             ", ".join([format_array(value) if isinstance(value, JavaArray)
                        else f"'{value}'" if isinstance(value, six.text_type)  # Remove 'u' prefix in Python 2 so tests are consistent.
                        else repr(value)
                        for value in array]) +
             "]")
