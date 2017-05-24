from cpython.version cimport PY_MAJOR_VERSION

from collections import OrderedDict
import re
import six
import sys

from cpython.object cimport PyObject
from libc.float cimport FLT_MAX

import chaquopy

INT_TYPES = "BSIJ"                          # Order matters: see is_assignable_from.
FLOAT_TYPES = "FD"                          #   "      "
NUMERIC_TYPES = INT_TYPES + FLOAT_TYPES     #   "      "
PRIMITIVE_TYPES = NUMERIC_TYPES + "CZ"      # Order doesn't matter here.

# In order of preference when assigning to a Number or Object.
BOXED_INT_TYPES = OrderedDict([("J", "Long"), ("I", "Integer"), ("S", "Short"), ("B", "Byte")])
BOXED_FLOAT_TYPES = OrderedDict([("D", "Double"), ("F", "Float")])
BOXED_NUMERIC_TYPES = OrderedDict(list(BOXED_INT_TYPES.items()) + list(BOXED_FLOAT_TYPES.items()))

ARRAY_CONVERSIONS = ["Ljava/lang/Object;", "Ljava/lang/Cloneable;", "Ljava/io/Serializable;"]

JCHAR_ENCODING = "UTF-16-LE" if sys.byteorder == "little" else "UTF-16-BE"


cdef void release_args(JNIEnv *j_env, tuple definition_args, jvalue *j_args, args) except *:
    cdef int index
    for index, argtype in enumerate(definition_args):
        if argtype[0] == 'L':
            j_env[0].DeleteLocalRef(j_env, j_args[index].l)
        elif argtype[0] == '[':
            # Copy back any modifications the Java method may have made to the array
            ret = j2p_array(j_env, argtype[1:], j_args[index].l)
            try:
                args[index][:] = ret
            except TypeError:
                pass    # The arg was a tuple or other read-only sequence.
            j_env[0].DeleteLocalRef(j_env, j_args[index].l)


# Cython auto-generates range checking code for the integral types.
cdef void populate_args(JNIEnv *j_env, tuple definition_args, jvalue *j_args, args) except *:
    cdef int index
    for index, argtype in enumerate(definition_args):
        py_arg = p2j(j_env, argtype, args[index])
        if argtype == 'Z':
            j_args[index].z = py_arg
        elif argtype == 'B':
            j_args[index].b = py_arg
        elif argtype == 'C':
            check_range_char(py_arg)
            j_args[index].c = ord(py_arg)
        elif argtype == 'S':
            j_args[index].s = py_arg
        elif argtype == 'I':
            j_args[index].i = py_arg
        elif argtype == 'J':
            j_args[index].j = py_arg
        elif argtype == 'F':
            check_range_float32(py_arg)
            j_args[index].f = py_arg
        elif argtype == 'D':
            j_args[index].d = py_arg
        elif argtype[0] in 'L[':
            j_args[index].l = (<JNIRef?>py_arg).return_ref(j_env)


cdef j2p(JNIEnv *j_env, JNIRef j_object):
    if not j_object:
        return None

    from chaquopy import autoclass
    r = lookup_java_object_name(j_env, j_object.obj)

    if r[0] == '[':
        return j2p_array(j_env, r[1:], j_object.obj)

    if r == 'java.lang.String':
        return j2p_string(j_env, j_object.obj)

    # Unboxing
    if r == 'java.lang.Long':
        return autoclass(r)(instance=j_object).longValue()
    if r == 'java.lang.Integer':
        return autoclass(r)(instance=j_object).intValue()
    if r == 'java.lang.Float':
        return autoclass(r)(instance=j_object).floatValue()
    if r == 'java.lang.Double':
        return autoclass(r)(instance=j_object).doubleValue()
    if r == 'java.lang.Short':
        return autoclass(r)(instance=j_object).shortValue()
    if r == 'java.lang.Boolean':
        return autoclass(r)(instance=j_object).booleanValue()
    if r == 'java.lang.Byte':
        return autoclass(r)(instance=j_object).byteValue()
    if r == 'java.lang.Character':
        return autoclass(r)(instance=j_object).charValue()

    if r == 'com.chaquo.python.PyObject':
        return j2p_pyobject(j_env, j_object.obj)

    # Failed to convert it, so return a proxy object.
    return autoclass(r)(instance=j_object)


cdef j2p_string(JNIEnv *j_env, jobject string):
    cdef const jchar *jchar_str
    # We can't decode directly from a jchar array because of
    # https://github.com/cython/cython/issues/1696 . This cdef is necessary to prevent Cython
    # inferring the type of bytes_str and calling the decode function directly.
    cdef object bytes_str

    # GetStringChars will crash if either of these are violated
    if string == NULL:
        raise ValueError("String cannot be null")
    if not j_env[0].IsInstanceOf(j_env, string,
                                 (<JavaObject?>find_javaclass("java.lang.String")).j_self.obj):
        raise TypeError("Object is not a String")

    jchar_str = j_env[0].GetStringChars(j_env, string, NULL)
    if jchar_str == NULL:
        raise Exception("GetStringChars failed")
    str_len = j_env[0].GetStringLength(j_env, string)
    bytes_str = (<char*>jchar_str)[:str_len * 2]  # See note at bytes_str cdef above
    j_env[0].ReleaseStringChars(j_env, string, jchar_str)
    return bytes_str.decode(JCHAR_ENCODING)


cdef j2p_pyobject(JNIEnv *env, jobject jpyobject):
    if jpyobject == NULL:
        return None
    JPyObject = chaquopy.autoclass("com.chaquo.python.PyObject")
    jpo = JPyObject(instance=GlobalRef.create(env, jpyobject))
    cdef PyObject *po = <PyObject*><jlong> jpo.addr
    if po == NULL:
        raise ValueError("PyObject is closed")
    return <object>po


# TODO #5178: return a proxy object instead, so the Java array can be modified.
cdef j2p_array(JNIEnv *j_env, definition, jobject j_object):

    if j_object == NULL:
        return None

    array_size = j_env[0].GetArrayLength(j_env, j_object)

    r = definition[0]
    if r == 'Z':
        j_booleans = j_env[0].GetBooleanArrayElements(j_env, j_object, NULL)
        ret = [bool(j_booleans[i]) for i in range(array_size)]
        j_env[0].ReleaseBooleanArrayElements(j_env, j_object, j_booleans, 0)

    elif r == 'B':
        j_bytes = j_env[0].GetByteArrayElements(j_env, j_object, NULL)
        ret = [j_bytes[i] for i in range(array_size)]
        j_env[0].ReleaseByteArrayElements(j_env, j_object, j_bytes, 0)

    elif r == 'C':
        j_chars = j_env[0].GetCharArrayElements(j_env, j_object, NULL)
        ret = [six.unichr(j_chars[i]) for i in range(array_size)]
        j_env[0].ReleaseCharArrayElements(j_env, j_object, j_chars, 0)

    elif r == 'S':
        j_shorts = j_env[0].GetShortArrayElements(j_env, j_object, NULL)
        ret = [j_shorts[i] for i in range(array_size)]
        j_env[0].ReleaseShortArrayElements(j_env, j_object, j_shorts, 0)

    elif r == 'I':
        j_ints = j_env[0].GetIntArrayElements(j_env, j_object, NULL)
        ret = [j_ints[i] for i in range(array_size)]
        j_env[0].ReleaseIntArrayElements(j_env, j_object, j_ints, 0)

    elif r == 'J':
        j_longs = j_env[0].GetLongArrayElements(j_env, j_object, NULL)
        ret = [j_longs[i] for i in range(array_size)]
        j_env[0].ReleaseLongArrayElements(j_env, j_object, j_longs, 0)

    elif r == 'F':
        j_floats = j_env[0].GetFloatArrayElements(j_env, j_object, NULL)
        ret = [j_floats[i] for i in range(array_size)]
        j_env[0].ReleaseFloatArrayElements(j_env, j_object, j_floats, 0)

    elif r == 'D':
        j_doubles = j_env[0].GetDoubleArrayElements(j_env, j_object, NULL)
        ret = [j_doubles[i] for i in range(array_size)]
        j_env[0].ReleaseDoubleArrayElements(j_env, j_object, j_doubles, 0)

    elif r in 'L[':
        ret = []
        for i in range(array_size):
            j_object_item = j_env[0].GetObjectArrayElement(j_env, j_object, i)
            check_exception(j_env)
            ret.append(j2p(j_env, LocalRef.adopt(j_env, j_object_item)))

    else:
        raise Exception(f"Invalid signature '{definition}'")

    return ret


# If the definition is for a Java object or array, returns a JNIRef.
# If the definition is for a Java primitive, returns a Python int/float/bool/str.
cdef p2j(JNIEnv *j_env, definition, obj, bint autobox=True):
    if definition == 'V':
        # Used to be a possibility when using java.lang.reflect.Proxy; keeping in case we do
        # something similar in the future.
        if obj is not None:
            raise TypeError("Void method cannot return a value")
        return LocalRef()

    # For primitive types we simply check type check and then return the Python value: it's
    # the caller's responsibility to convert it to the C type. It's also the caller's
    # responsibility to perform range checks: see note at is_applicable_arg for why we can't do
    # it here.
    #
    # We don't implement auto-unboxing, because the boxed types are automatically unboxed by
    # j2p and should therefore never normally be touched by Python user code. Auto-boxing, on
    # the other hand, will be done if necessary below.
    elif definition in PRIMITIVE_TYPES:
        if definition == 'Z':
            if isinstance(obj, bool):
                return obj
            if isinstance(obj, chaquopy.jboolean):
                return obj.value

        elif definition in INT_TYPES:
            # Java allows a char to be implicitly converted to an int or larger, but this would
            # be surprising in Python. Require the user to be explicit and use the function `ord`.
            #
            # For backwards compatibility with old versions of Python, bool is a subclass of
            # int, but we should be stricter.
            if isinstance(obj, six.integer_types) and not isinstance(obj, bool):
                return obj
            if isinstance(obj, chaquopy.IntPrimitive) and \
               INT_TYPES.find(obj.sig) <= INT_TYPES.find(definition):
                return obj.value

        elif definition in FLOAT_TYPES:
            if isinstance(obj, (float, six.integer_types)) and not isinstance(obj, bool):
                return obj
            if isinstance(obj, chaquopy.NumericPrimitive) and \
               NUMERIC_TYPES.find(obj.sig) <= NUMERIC_TYPES.find(definition):
                return obj.value

        elif definition == "C":
            # We don't check that len(obj) == 1; see note above about range checks.
            if isinstance(obj, six.string_types):
                return obj
            if isinstance(obj, chaquopy.jchar):
                return obj.value

        else:
            raise Exception(f"Unknown primitive type {definition}")

    elif definition[0] == 'L':
        clsname = definition[1:-1].replace("/", ".")
        klass = find_javaclass(clsname)

        if obj is None:
            return LocalRef()

        elif isinstance(obj, (six.string_types, chaquopy.jchar)):
            if isinstance(obj, six.string_types):
                String = find_javaclass("java.lang.String")
                if klass.isAssignableFrom(String):
                    u = obj.decode('ASCII') if isinstance(obj, bytes) else obj
                    utf16 = u.encode(JCHAR_ENCODING)
                      # len(u) doesn't necessarily equal len(utf16)//2 on a "narrow" Python build.
                    return LocalRef.adopt(j_env, j_env[0].NewString(j_env,
                                                                    <jchar*><char*>utf16,
                                                                    len(utf16)//2))
            if autobox:
                Character = find_javaclass("java.lang.Character")
                if klass.isAssignableFrom(Character):
                    return p2j_box(j_env, Character, obj)

        elif isinstance(obj, (bool, chaquopy.jboolean)):
            if autobox:
                Boolean = find_javaclass("java.lang.Boolean")
                if klass.isAssignableFrom(Boolean):
                    return p2j_box(j_env, Boolean, obj)
        elif isinstance(obj, (six.integer_types, chaquopy.IntPrimitive)):
            if autobox:
                # TODO #5174 support BigInteger, and make that a final fallback if clsname is
                # Number or Object, and Long isn't big enough.
                #
                # Automatic primitive conversion cannot be combined with autoboxing (JLS 5.3).
                box_clsnames = ([BOXED_NUMERIC_TYPES[obj.sig]] if isinstance(obj, chaquopy.IntPrimitive)
                                else BOXED_NUMERIC_TYPES.values())
                for box_clsname in box_clsnames:
                    box_klass = find_javaclass("java.lang." + box_clsname)
                    if klass.isAssignableFrom(box_klass):
                        return p2j_box(j_env, box_klass, obj)
        elif isinstance(obj, (float, chaquopy.FloatPrimitive)):
            if autobox:
                # Automatic primitive conversion cannot be combined with autoboxing (JLS 5.3).
                box_clsnames = ([BOXED_FLOAT_TYPES[obj.sig]] if isinstance(obj, chaquopy.FloatPrimitive)
                                else BOXED_FLOAT_TYPES.values())
                for box_clsname in box_clsnames:
                    box_klass = find_javaclass("java.lang." + box_clsname)
                    if klass.isAssignableFrom(box_klass):
                        return p2j_box(j_env, box_klass, obj)

        elif isinstance(obj, JavaObject):
            # Comparison to clsname prevents recursion when converting argument to isAssignableFrom
            if clsname == obj.__javaclass__ or \
               klass.isAssignableFrom(find_javaclass(obj.__javaclass__)):
                return (<JavaObject?>obj).j_self
        elif isinstance(obj, JavaClass):
            if klass.isAssignableFrom(find_javaclass("java.lang.Class")):
                return <GlobalRef?>obj.j_cls
        elif assignable_to_array(definition, obj):  # Can only be via ARRAY_CONVERSIONS
            return LocalRef.adopt(j_env, p2j_array(j_env, "Ljava/lang/Object;", obj))

        # Anything, including the above types, can be converted to a PyObject if the signature
        # will accept it.
        elif klass.isAssignableFrom(find_javaclass("com.chaquo.python.PyObject")):
            return LocalRef.adopt(j_env, p2j_pyobject(j_env, obj))

    elif definition[0] == '[':
        if assignable_to_array(definition, obj):
            return LocalRef.adopt(j_env, p2j_array(j_env, definition[1:], obj))

    else:
        raise ValueError(f"Invalid signature '{definition}'")

    # TODO #5155 don't expose JNI signatures to users
    raise TypeError(f"Cannot convert {type(obj).__name__} object to {definition}")


# Because of the caching in JavaMultipleMethod, the result of this function must only be
# affected by the object type, not its value.
def assignable_to_array(definition, obj):
    if not (definition.startswith("[") or definition in ARRAY_CONVERSIONS):
        return False
    if obj is None:
        return True
    if isinstance(obj, six.string_types):
        return False  # Introduces too many complications.
    if isinstance(obj, chaquopy.ArrayWrapper):
        return find_javaclass(definition).isAssignableFrom(find_javaclass(obj.sig))

    # All other iterable types are convertible to arrays.
    try:
        iter(obj)
        return True
    except TypeError:
        return False


# https://github.com/cython/cython/issues/1709
#
# TODO #5182 we should also test against FLT_MIN, which is the most infintesimal float32, to
# avoid accidental conversion to zero.
def check_range_float32(value):
    if value not in [float("nan"), float("inf"), float("-inf")] and \
       (value < -FLT_MAX or value > FLT_MAX):
        raise OverflowError("value too large to convert to float")


# `ord` will raise a TypeError if not passed a string of length 1. In "narrow" Python builds, a
# non-BMP character is represented as a string of length 2, so avoid a potentially confusing
# error message.
def check_range_char(value):
    if (len(value) == 2 and re.match(u'[\ud800-\udbff][\udc00-\udfff]', value, re.UNICODE)) or \
       ord(value) > 0xFFFF:
        raise TypeError("Cannot convert non-BMP character to char")


cdef JNIRef p2j_string(JNIEnv *env, s):
    return p2j(env, "Ljava/lang/String;", s)


cdef JNIRef p2j_box(JNIEnv *env, box_klass, value):
    if isinstance(value, chaquopy.Primitive):
        value = value.value

    # Uniquely among the boxed types, the Float class has two primitive-typed constructors, one
    # of which takes a double, which our overload resolution will prefer.
    clsname = box_klass.getName()
    if clsname == "java.lang.Float":
        check_range_float32(value)

    # This will result in a recursive call to p2j, this time requesting the primitive type of
    # the constructor parameter. Range checks will be performed by populate_args.
    cdef JavaObject boxed = chaquopy.autoclass(clsname)(value)
    return boxed.j_self


cdef jobject p2j_pyobject(JNIEnv *env, obj) except *:
    if obj is None:
        return NULL
    # Can't call getInstance() using autoclass because that'll immediately unwrap the
    # returned proxy object (see j2p)
    JPyObject = chaquopy.autoclass("com.chaquo.python.PyObject")
    cdef jobject j_pyobject = env[0].CallStaticObjectMethod \
        (env,
         (<GlobalRef?>JPyObject.j_cls).obj,
         (<JavaMethod?>JPyObject.__dict__["getInstance"]).id(),
         <jlong><PyObject*>obj)
    check_exception(env)
    return j_pyobject


cdef jobject p2j_array(JNIEnv *j_env, definition, pyarray) except *:
    """`definition` is the element type, not the array type.
    """
    if isinstance(pyarray, chaquopy.ArrayWrapper):
        pyarray = pyarray.value
    if pyarray is None:
        return NULL

    array_size = len(pyarray)
    pyarray_checked = [p2j(j_env, definition, pyarray[i]) for i in range(array_size)]

    if definition == 'Z':
        ret = j_env[0].NewBooleanArray(j_env, array_size)
        z_array = j_env[0].GetBooleanArrayElements(j_env, ret, NULL)
        for i in range(array_size):
            z_array[i] = pyarray_checked[i]
        j_env[0].ReleaseBooleanArrayElements(j_env, ret, z_array, 0)

    elif definition == 'B':
        ret = j_env[0].NewByteArray(j_env, array_size)
        b_array = j_env[0].GetByteArrayElements(j_env, ret, NULL)
        for i in range(array_size):
            b_array[i] = pyarray_checked[i]
        j_env[0].ReleaseByteArrayElements(j_env, ret, b_array, 0)

    elif definition == 'C':
        ret = j_env[0].NewCharArray(j_env, array_size)
        c_array = j_env[0].GetCharArrayElements(j_env, ret, NULL)
        for i in range(array_size):
            c = pyarray_checked[i]
            check_range_char(c)
            c_array[i] = ord(c)
        j_env[0].ReleaseCharArrayElements(j_env, ret, c_array, 0)

    elif definition == 'S':
        ret = j_env[0].NewShortArray(j_env, array_size)
        s_array = j_env[0].GetShortArrayElements(j_env, ret, NULL)
        for i in range(array_size):
            s_array[i] = pyarray_checked[i]
        j_env[0].ReleaseShortArrayElements(j_env, ret, s_array, 0)

    elif definition == 'I':
        ret = j_env[0].NewIntArray(j_env, array_size)
        i_array = j_env[0].GetIntArrayElements(j_env, ret, NULL)
        for i in range(array_size):
            i_array[i] = pyarray_checked[i]
        j_env[0].ReleaseIntArrayElements(j_env, ret, i_array, 0)

    elif definition == 'J':
        ret = j_env[0].NewLongArray(j_env, array_size)
        j_array = j_env[0].GetLongArrayElements(j_env, ret, NULL)
        for i in range(array_size):
            j_array[i] = pyarray_checked[i]
        j_env[0].ReleaseLongArrayElements(j_env, ret, j_array, 0)

    elif definition == 'F':
        ret = j_env[0].NewFloatArray(j_env, array_size)
        f_array = j_env[0].GetFloatArrayElements(j_env, ret, NULL)
        for i in range(array_size):
            f = pyarray_checked[i]
            check_range_float32(f)
            f_array[i] = f
        j_env[0].ReleaseFloatArrayElements(j_env, ret, f_array, 0)

    elif definition == 'D':
        ret = j_env[0].NewDoubleArray(j_env, array_size)
        d_array = j_env[0].GetDoubleArrayElements(j_env, ret, NULL)
        for i in range(array_size):
            d_array[i] = pyarray_checked[i]
        j_env[0].ReleaseDoubleArrayElements(j_env, ret, d_array, 0)

    elif definition[0] in 'L[':
        clsname = definition[1:-1] if (definition[0] == 'L') else definition
        j_class = CQPEnv().FindClass(clsname)
        ret = j_env[0].NewObjectArray(j_env, array_size, j_class.obj, NULL)
        for i in range(array_size):
            j_env[0].SetObjectArrayElement(j_env, ret, i, (<JNIRef?>pyarray_checked[i]).obj)
            check_exception(j_env)

    else:
        raise ValueError(f"Invalid signature '{definition}'")

    return ret
