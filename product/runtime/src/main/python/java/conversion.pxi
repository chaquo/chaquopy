from cpython.version cimport PY_MAJOR_VERSION

from itertools import chain
import re

from cpython.object cimport PyObject
from cpython.ref cimport Py_INCREF
from libc.float cimport FLT_MAX

numpy = None  # Initialized by importer.py.


# In order of size.
INT_TYPES = OrderedDict([("J", "Long"), ("I", "Integer"), ("S", "Short"), ("B", "Byte")])
FLOAT_TYPES = OrderedDict([("D", "Double"), ("F", "Float")])
NUMERIC_TYPES = OrderedDict(list(FLOAT_TYPES.items()) + list(INT_TYPES.items()))
PRIMITIVE_TYPES = dict([("C", "Character"), ("Z", "Boolean")] + list(NUMERIC_TYPES.items()))

UNBOX_METHODS = {f"Ljava/lang/{boxed};": f"{unboxed}Value" for boxed, unboxed in
                 [("Boolean", "boolean"), ("Byte", "byte"), ("Short", "short"), ("Integer", "int"),
                  ("Long", "long"), ("Float", "float"), ("Double", "double"), ("Character", "char")]}

ARRAY_CONVERSIONS = ["Ljava/lang/Object;", "Ljava/lang/Cloneable;", "Ljava/io/Serializable;"]

# This must be a DEF to allow Cython to generate optimized calls of the decode and encode
# functions. We don't currently support any big-endian platforms, and the unit tests will
# detect if that ever changes.
DEF JCHAR_ENCODING = "UTF-16-LE"


# Useful if d is an OrderedDict.
cdef dict_index(d, key):
    for i, k in enumerate(d):
        if k == key:
            return i
    raise KeyError(key)


# Copy back any modifications the Java method may have made to mutable parameters.
cdef copy_output_args(CQPEnv env, args, p2j_args):
    for arg, p2j_arg in zip(args, p2j_args):
        if isinstance(p2j_arg, JNIRef) and p2j_arg:
            argtype = object_sig(env, p2j_arg)
            if argtype[0] == "[" and not isinstance(arg, JavaArray):
                ret = jarray(argtype[1:])(instance=p2j_arg)
                try:
                    arg[:] = ret
                except TypeError:
                    pass    # The arg was a tuple or other read-only sequence.


# Cython auto-generates range checking code for the integral types.
cdef populate_args(JavaMethod jm, p2j_args, jvalue *j_args):
    for index, argtype in enumerate(jm.args_sig):
        py_arg = p2j_args[index]
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
            j_args[index].l = (<JNIRef?>py_arg).obj


cdef j2p(JNIEnv *j_env, JNIRef j_object):
    if not j_object:
        return None
    env = CQPEnv.wrap(j_env)
    j_klass = env.GetObjectClass(j_object)

    sig = klass_sig(env, j_klass)
    if sig == 'Ljava/lang/String;':
        return j2p_string(j_env, j_object)
    if sig == 'Lcom/chaquo/python/PyObject;':
        return j2p_pyobject(j_env, j_object.obj)

    unbox_method = UNBOX_METHODS.get(sig)
    if unbox_method:
        return getattr(jclass(sig)(instance=j_object), unbox_method)()

    return jclass_from_j_klass(sig, j_klass)(instance=j_object)


# j_string MUST be a (possibly-null) String, or there may be a native crash.
cdef unicode j2p_string(JNIEnv *j_env, JNIRef j_string):
    if not j_string:
        raise ValueError("String cannot be null")

    cdef const jchar *jchar_str = j_env[0].GetStringChars(j_env, j_string.obj, NULL)
    if jchar_str == NULL:
        raise Exception("GetStringChars failed")
    cdef int str_len = j_env[0].GetStringLength(j_env, j_string.obj)
    s = (<char*>jchar_str)[:str_len * 2].decode(JCHAR_ENCODING)  # 2 bytes/char for UTF-16.
    j_env[0].ReleaseStringChars(j_env, j_string.obj, jchar_str)
    return s


# jpyobject MUST be a (possibly-null) PyObject, or there may be a native crash.
#
# This function is called from PyObject.getInstance, which is synchronized on PyObject.cache.
# To avoid deadlocks, it must not do anything which requires a lock, including calling jclass()
# or creating jclass instances.
cdef j2p_pyobject(JNIEnv *j_env, jobject jpyobject):
    if jpyobject == NULL:
        return None

    global fid_PyObject_addr
    if not fid_PyObject_addr:
        env = CQPEnv.wrap(j_env)
        j_PyObject = env.FindClass("com.chaquo.python.PyObject")
        fid_PyObject_addr = env.GetFieldID(j_PyObject, "addr", "J")

    cdef PyObject *po = <PyObject*> j_env[0].GetLongField(j_env, jpyobject, fid_PyObject_addr)
    if po == NULL:
        raise ValueError("PyObject is closed")
    return <object>po

cdef jfieldID fid_PyObject_addr = NULL


# If the definition is for a Java object or array, returns a JNIRef.
# If the definition is for a Java primitive, returns a Python int/float/bool/str.
cdef p2j(JNIEnv *j_env, definition, obj, bint autobox=True):
    # Can happen when calling a proxy method. If the Python implementation returns anything but
    # None, the error at the bottom of this function will be raised.
    if definition == 'V':
        if obj is None:
            return LocalRef()

    # For primitive types we simply check type check and then return the Python value: it's
    # the caller's responsibility to convert it to the C type. It's also the caller's
    # responsibility to perform range checks: see note at is_applicable_arg for why we can't do
    # it here.
    #
    # We don't do auto-unboxing here, because boxed types are automatically unboxed by j2p and
    # will therefore never be touched by Python user code unless created explicitly.
    # Auto-boxing, on the other hand, will be done if necessary below.
    elif definition == 'Z':
        if isinstance(obj, bool):
            return obj
        if isinstance(obj, primitive.jboolean):
            return obj.value
        if numpy and isinstance(obj, numpy.bool_):
            return obj.item()
    elif definition in INT_TYPES:
        # Java allows a char to be implicitly converted to an int or larger, but this would
        # be surprising in Python. Require the user to be explicit and use the function `ord`.
        #
        # bool is a subclass of int in Python, but allowing implicit conversion from Python
        # bool to Java integer types could cause ambiguity in overloads.
        if isinstance(obj, int) and not isinstance(obj, bool):
            return obj
        if isinstance(obj, IntPrimitive) and \
           dict_index(INT_TYPES, obj.sig) >= dict_index(INT_TYPES, definition):
            return obj.value
        if numpy and isinstance(obj, numpy.integer):
            return obj.item()
    elif definition in FLOAT_TYPES:
        if isinstance(obj, (float, int)) and not isinstance(obj, bool):
            return obj
        if isinstance(obj, NumericPrimitive) and \
           dict_index(NUMERIC_TYPES, obj.sig) >= dict_index(NUMERIC_TYPES, definition):
            return obj.value
        if numpy and isinstance(obj, (numpy.integer, numpy.floating)):
            return obj.item()
    elif definition == "C":
        # We don't check that len(obj) == 1; see note above about range checks.
        if isinstance(obj, unicode):
            return obj
        if isinstance(obj, primitive.jchar):
            return obj.value

    elif definition[0] == 'L':
        env = CQPEnv.wrap(j_env)
        j_klass = env.FindClass(definition)

        if obj is None:
            return LocalRef()
        elif isinstance(obj, NoneCast):
            if env.IsAssignableFrom(env.FindClass(obj.sig), j_klass):
                return LocalRef()

        elif isinstance(obj, (unicode, primitive.jchar)):
            if isinstance(obj, unicode):
                if env.IsAssignableFrom(env.FindClass("java.lang.String"), j_klass):
                    return p2j_string(j_env, obj)
            if autobox:
                boxed = p2j_box(env, j_klass, "Character", obj)
                if boxed: return boxed

        elif isinstance(obj, (bool, primitive.jboolean)):
            if autobox:
                boxed = p2j_box(env, j_klass, "Boolean", obj)
                if boxed: return boxed
        elif isinstance(obj, (int, primitive.IntPrimitive)):
            if autobox:
                # Automatic primitive conversion cannot be combined with autoboxing (JLS 5.3).
                box_cls_names = ([NUMERIC_TYPES[obj.sig]] if isinstance(obj, IntPrimitive)
                                 else chain(INT_TYPES.values(), FLOAT_TYPES.values()))
                for box_cls_name in box_cls_names:
                    boxed = p2j_box(env, j_klass, box_cls_name, obj)
                    if boxed: return boxed
        elif isinstance(obj, (float, FloatPrimitive)):
            if autobox:
                # Automatic primitive conversion cannot be combined with autoboxing (JLS 5.3).
                box_cls_names = ([FLOAT_TYPES[obj.sig]] if isinstance(obj, FloatPrimitive)
                                 else FLOAT_TYPES.values())
                for box_cls_name in box_cls_names:
                    boxed = p2j_box(env, j_klass, box_cls_name, obj)
                    if boxed: return boxed

        elif isinstance(obj, JavaObject):
            # See note at is_applicable_arg for why we don't use IsInstanceOf with _chaquopy_this.
            if env.IsAssignableFrom(<JNIRef?>type(obj)._chaquopy_j_klass, j_klass):
                return obj._chaquopy_this
        elif isinstance(obj, JavaClass):
            if env.IsAssignableFrom(env.FindClass("java.lang.Class"), j_klass):
                return <JNIRef?>obj._chaquopy_j_klass
        elif assignable_to_array(env, definition, obj):  # Can only be via ARRAY_CONVERSIONS
            return p2j_array("Ljava/lang/Object;", obj)

        # Anything, including the above types, can be converted to a PyObject. (We don't use
        # IsAssignableFrom here, because allowing conversion to Object could cause excessive
        # ambiguity in overload resolution.)
        if definition == "Lcom/chaquo/python/PyObject;":
            return p2j_pyobject_ref(env, obj)

    elif definition[0] == '[':
        env = CQPEnv.wrap(j_env)
        if assignable_to_array(env, definition, obj):
            return p2j_array(definition[1:], obj)

    else:
        raise ValueError(f"Invalid signature '{definition}'")

    raise TypeError(f"Cannot convert {type(obj).__name__} object to {sig_to_java(definition)}")


# Because of the caching in JavaMultipleMethod, the result of this function must only be
# affected by the object type, not its value.
cdef assignable_to_array(CQPEnv env, definition, obj):
    if not (definition.startswith("[") or (definition in ARRAY_CONVERSIONS)):
        return False
    if obj is None:
        return True
    if isinstance(obj, (JavaArray, NoneCast)):
        return env.IsAssignableFrom(env.FindClass(jni_sig(type(obj))),
                                    env.FindClass(definition))

    # All other iterable types are assignable to all array types, except strings, which would
    # introduce too many complications in overload resolution.
    try:
        iter(obj)
        return not isinstance(obj, unicode)
    except TypeError:
        return False


cdef JNIRef p2j_array(element_type, obj):
    if obj is None or isinstance(obj, NoneCast):
        return LocalRef()

    if isinstance(obj, JavaArray):
        java_array = obj
    else:
        java_array = jarray(element_type)(obj)
    return java_array._chaquopy_this


# Unlike with integers, Cython doesn't do any checks for overflow (to infinity) or
# underflow (to zero) when converting a 64-bit Python float to a 32-bit C float. We
# currently check for overflow and not underflow, but since this behavior of float types
# is well-known, maybe we shouldn't be checking for either
# (https://github.com/cython/cython/issues/1709).
#
# cpdef because it's called from primitive.py.
cpdef check_range_float32(value):
    if value not in [float("nan"), float("inf"), float("-inf")] and \
       (value < -FLT_MAX or value > FLT_MAX):
        # Same wording as Cython integer overflow errors.
        raise OverflowError("value too large to convert to float")


# cpdef because it's called from primitive.py.
cpdef check_range_char(value):
    # In our current version of Cython, `ord` will raise a ValueError if not passed a string of
    # length 1.
    if ord(value) > 0xFFFF:
        raise TypeError("Cannot convert non-BMP character to char")


cdef JNIRef p2j_string(JNIEnv *j_env, unicode s):
    # Python strings can contain invalid surrogates, but Java strings cannot.
    # "backslashreplace" would retain some information about the invalid character, but
    # we don't know what context this string will be used in, so changing its length
    # could cause much worse confusion.
    utf16 = s.encode(JCHAR_ENCODING, errors="replace")
    return LocalRef.adopt(j_env, j_env[0].NewString(
        j_env, <jchar*><char*>utf16, len(utf16)//2))  # 2 bytes/char for UTF-16.


cdef box_sig(JNIEnv *j_env, JNIRef j_klass):
    original_sig = klass_sig(CQPEnv.wrap(j_env), j_klass)
    box_cls_name = PRIMITIVE_TYPES.get(original_sig)
    return f"Ljava/lang/{box_cls_name};" if box_cls_name else original_sig


cdef JNIRef p2j_box(CQPEnv env, JNIRef j_klass, str box_cls_name, value):
    full_box_cls_name = "java.lang." + box_cls_name
    j_box_klass = env.FindClass(full_box_cls_name)
    if not env.IsAssignableFrom(j_box_klass, j_klass):
        return None

    if isinstance(value, Primitive):
        value = value.value

    # Uniquely among the boxed types, the Float class has two primitive-typed constructors, one
    # of which takes a double, which our overload resolution will prefer.
    if box_cls_name == "Float":
        check_range_float32(value)

    # This will result in a recursive call to p2j, this time requesting the primitive type of
    # the constructor parameter. Range checks will be performed by populate_args.
    return jclass(full_box_cls_name)(value)._chaquopy_this


cdef jlong p2j_pyobject(JNIEnv *j_env, obj) except? 0:
    if obj is None:
        return 0
    else:
        Py_INCREF(obj)  # Matches with DECREF in closeNative.
        return <jlong><PyObject*>obj


cdef GlobalRef j_PyObject
cdef jmethodID mid_PyObject_getInstance = NULL

cdef JNIRef p2j_pyobject_ref(CQPEnv env, obj):
    # Can't call getInstance() using jclass because that'll immediately unwrap the
    # returned proxy object (see j2p)
    global j_PyObject, mid_PyObject_getInstance
    if not mid_PyObject_getInstance:
        j_PyObject = env.FindClass("com.chaquo.python.PyObject")
        mid_PyObject_getInstance = env.GetStaticMethodID(j_PyObject, "getInstance",
                                                         "(J)Lcom/chaquo/python/PyObject;")
    cdef jvalue j_args[1]
    j_args[0].j = p2j_pyobject(env.j_env, obj)
    return env.CallStaticObjectMethodA(j_PyObject, mid_PyObject_getInstance, j_args)
