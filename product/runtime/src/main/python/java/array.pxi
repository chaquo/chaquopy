import collections
import itertools


class JavaArray(collections.Sequence):
    def __new__(cls, value=None, *, instance=None):
        if value is None and not instance:  # instance may also be a null JNIRef.
            return cast(cls, None)
        else:
            return super(JavaArray, cls).__new__(cls, value, instance=instance)

    def __init__(self, value=None, *, JNIRef instance=None):
        env = CQPEnv()
        if instance:
            assert value is None
            if not env.IsInstanceOf(instance, env.FindClass(self.sig)):
                instance_sig = lookup_java_object_name(env.j_env, instance.obj)
                raise TypeError(f"cannot create {java.sig_to_java(self.sig)} proxy from "
                                f"{java.sig_to_java(instance_sig)} instance")
            self._chaquopy_this = instance.global_ref()
        else:
            assert instance is None
            length = len(value)
            r = self.sig[1]
            if r == "Z":
                array = env.NewBooleanArray(length)
            elif r == "B":
                array = env.NewByteArray(length)
            elif r == "S":
                array = env.NewShortArray(length)
            elif r == "I":
                array = env.NewIntArray(length)
            elif r == "J":
                array = env.NewLongArray(length)
            elif r == "F":
                array = env.NewFloatArray(length)
            elif r == "D":
                array = env.NewDoubleArray(length)
            elif r == "C":
                array = env.NewCharArray(length)
            elif r in "L[":
                array = env.NewObjectArray(length, env.FindClass(self.sig[1:]))
            else:
                raise ValueError(f"Invalid signature '{self.sig}'")
            self._chaquopy_this = (<JNIRef?>array).global_ref()

            for i, v in enumerate(value):
                self[i] = v

    def __repr__(self):
        return f"jarray('{self.sig[1:]}')({self.array_repr()})"

    def array_repr(self):
        return  ("[" +
                 ", ".join([value.array_repr() if isinstance(value, JavaArray)
                            else f"'{value}'" if isinstance(value, six.text_type)  # Remove 'u' prefix in Python 2 so tests are consistent.
                            else repr(value)
                            for value in self]) +
                 "]")

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
                    all([value == other[i] for i, value in enumerate(self)]))
        except TypeError:
            return NotImplemented

    def __ne__(self, other):
        eq = self == other
        return eq if (eq == NotImplemented) else (not eq)

    # Like Python lists, jarray objects should be unhashable because they're mutable.
    __hash__ = None

    def __add__(self, other):
        return list(itertools.chain(self, other))
    def __radd__(self, other):
        return list(itertools.chain(other, self))

    def _chaquopy_get(self, index):
        env = CQPEnv()
        cdef JNIRef this = self._chaquopy_this
        r = self.sig[1]
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
            raise ValueError(f"Invalid signature '{self.sig}'")

    def _chaquopy_set(self, index, value):
        env = CQPEnv()
        cdef JNIRef this = self._chaquopy_this
        # TODO #5209 use actual rather than declared signature: old Android versions don't
        # type-check correctly.
        value_p2j = p2j(env.j_env, self.sig[1:], value)
        r = self.sig[1]
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
            raise ValueError(f"Invalid signature '{self.sig}'")
