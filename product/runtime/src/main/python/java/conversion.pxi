from cpython.version cimport PY_MAJOR_VERSION

from collections import OrderedDict
from itertools import chain
import re
import sys

from cpython.object cimport PyObject
from libc.float cimport FLT_MAX

# In order of size.
INT_TYPES = OrderedDict([("J", "Long"), ("I", "Integer"), ("S", "Short"), ("B", "Byte")])
FLOAT_TYPES = OrderedDict([("D", "Double"), ("F", "Float")])
NUMERIC_TYPES = OrderedDict(list(FLOAT_TYPES.items()) + list(INT_TYPES.items()))
PRIMITIVE_TYPES = dict([("C", "Character"), ("Z", "Boolean")] + list(NUMERIC_TYPES.items()))

UNBOX_METHODS = {f"Ljava/lang/{boxed};": f"{unboxed}Value" for boxed, unboxed in
                 [("Boolean", "boolean"), ("Byte", "byte"), ("Short", "short"), ("Integer", "int"),
                  ("Long", "long"), ("Float", "float"), ("Double", "double"), ("Character", "char")]}

ARRAY_CONVERSIONS = ["Ljava/lang/Object;", "Ljava/lang/Cloneable;", "Ljava/io/Serializable;"]

JCHAR_ENCODING = "UTF-16-LE" if sys.byteorder == "little" else "UTF-16-BE"


# Copy back any modifications the Java method may have made to mutable parameters.
def copy_output_args(definition_args, args, p2j_args):
    for argtype, arg, p2j_arg in six.moves.zip(definition_args, args, p2j_args):
        if (argtype[0] == "[") and arg and (not isinstance(arg, JavaArray)):
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

    sig = object_sig(CQPEnv.wrap(j_env), j_object)
    if sig == 'Ljava/lang/String;':
        return j2p_string(j_env, j_object)
    if sig == 'Lcom/chaquo/python/PyObject;':
        return j2p_pyobject(j_env, j_object.obj)

    unbox_method = UNBOX_METHODS.get(sig)
    if unbox_method:
        return getattr(jclass(sig)(instance=j_object), unbox_method)()

    return jclass(sig)(instance=j_object)


cdef j2p_string(JNIEnv *j_env, JNIRef j_string):
    # GetStringChars will crash if either of these prerequisites are violated.
    if not j_string:
        raise ValueError("String cannot be null or None")
    env = CQPEnv()
    if not env.IsInstanceOf(j_string, env.FindClass("java.lang.String")):
        raise TypeError("Object is not a String")

    cdef const jchar *jchar_str = j_env[0].GetStringChars(j_env, j_string.obj, NULL)
    if jchar_str == NULL:
        raise Exception("GetStringChars failed")
    str_len = j_env[0].GetStringLength(j_env, j_string.obj)

    # We can't decode directly from a jchar array because of
    # https://github.com/cython/cython/issues/1696 . This cdef is necessary to prevent Cython
    # inferring the type of bytes_str and calling the decode function directly.
    cdef object bytes_str = (<char*>jchar_str)[:str_len * 2]  # See note at bytes_str cdef above
    j_env[0].ReleaseStringChars(j_env, j_string.obj, jchar_str)
    return bytes_str.decode(JCHAR_ENCODING)


cdef j2p_pyobject(JNIEnv *env, jobject jpyobject):
    if jpyobject == NULL:
        return None
    JPyObject = jclass("com.chaquo.python.PyObject")
    jpo = JPyObject(instance=GlobalRef.create(env, jpyobject))
    cdef PyObject *po = <PyObject*><jlong> jpo.addr
    if po == NULL:
        raise ValueError("PyObject is closed")
    return <object>po


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
        if isinstance(obj, java.jboolean):
            return obj.value
    elif definition in INT_TYPES:
        # Java allows a char to be implicitly converted to an int or larger, but this would
        # be surprising in Python. Require the user to be explicit and use the function `ord`.
        #
        # For backwards compatibility with old versions of Python, bool is a subclass of
        # int, but we should be stricter.
        if isinstance(obj, six.integer_types) and not isinstance(obj, bool):
            return obj
        if isinstance(obj, java.IntPrimitive) and \
           INT_TYPES.keys().index(obj.sig) >= INT_TYPES.keys().index(definition):
            return obj.value
    elif definition in FLOAT_TYPES:
        if isinstance(obj, (float, six.integer_types)) and not isinstance(obj, bool):
            return obj
        if isinstance(obj, java.NumericPrimitive) and \
           NUMERIC_TYPES.keys().index(obj.sig) >= NUMERIC_TYPES.keys().index(definition):
            return obj.value
    elif definition == "C":
        # We don't check that len(obj) == 1; see note above about range checks.
        if isinstance(obj, six.string_types):
            return obj
        if isinstance(obj, java.jchar):
            return obj.value

    elif definition[0] == 'L':
        env = CQPEnv()
        j_klass = env.FindClass(definition)

        if obj is None:
            return LocalRef()
        elif isinstance(obj, NoneCast):
            if env.IsAssignableFrom(env.FindClass(obj.sig), j_klass):
                return LocalRef()

        elif isinstance(obj, (six.string_types, java.jchar)):
            if isinstance(obj, six.string_types):
                if env.IsAssignableFrom(env.FindClass("java.lang.String"), j_klass):
                    u = obj.decode('ASCII') if isinstance(obj, bytes) else obj
                    utf16 = u.encode(JCHAR_ENCODING)
                      # len(u) doesn't necessarily equal len(utf16)//2 on a "narrow" Python build.
                    return LocalRef.adopt(j_env, j_env[0].NewString(j_env,
                                                                    <jchar*><char*>utf16,
                                                                    len(utf16)//2))
            if autobox:
                boxed = p2j_box(env, j_klass, "Character", obj)
                if boxed: return boxed

        elif isinstance(obj, (bool, java.jboolean)):
            if autobox:
                boxed = p2j_box(env, j_klass, "Boolean", obj)
                if boxed: return boxed
        elif isinstance(obj, (six.integer_types, java.IntPrimitive)):
            if autobox:
                # TODO #5174 support BigInteger, and make that a final fallback if clsname is
                # Number or Object, and Long isn't big enough.
                #
                # Automatic primitive conversion cannot be combined with autoboxing (JLS 5.3).
                box_cls_names = ([NUMERIC_TYPES[obj.sig]] if isinstance(obj, java.IntPrimitive)
                                 else chain(INT_TYPES.values(), FLOAT_TYPES.values()))
                for box_cls_name in box_cls_names:
                    boxed = p2j_box(env, j_klass, box_cls_name, obj)
                    if boxed: return boxed
        elif isinstance(obj, (float, java.FloatPrimitive)):
            if autobox:
                # Automatic primitive conversion cannot be combined with autoboxing (JLS 5.3).
                box_cls_names = ([FLOAT_TYPES[obj.sig]] if isinstance(obj, java.FloatPrimitive)
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
        elif assignable_to_array(definition, obj):  # Can only be via ARRAY_CONVERSIONS
            return p2j_array("Ljava/lang/Object;", obj)

        # Anything, including the above types, can be converted to a PyObject. (We don't use
        # IsAssignableFrom here, because allowing conversion to Object could cause excessive
        # ambiguity in overload resolution.)
        if definition == "Lcom/chaquo/python/PyObject;":
            return LocalRef.adopt(j_env, p2j_pyobject(j_env, obj))

    elif definition[0] == '[':
        if assignable_to_array(definition, obj):
            return p2j_array(definition[1:], obj)

    else:
        raise ValueError(f"Invalid signature '{definition}'")

    raise TypeError(f"Cannot convert {type(obj).__name__} object to {java.sig_to_java(definition)}")


# Because of the caching in JavaMultipleMethod, the result of this function must only be
# affected by the object type, not its value.
def assignable_to_array(definition, obj):
    if not (definition.startswith("[") or (definition in ARRAY_CONVERSIONS)):
        return False
    if obj is None:
        return True
    if isinstance(obj, (JavaArray, NoneCast)):
        env = CQPEnv()
        return env.IsAssignableFrom(env.FindClass(java.jni_sig(type(obj))),
                                    env.FindClass(definition))

    # All other iterable types are assignable to all array types, except strings, which would
    # introduce too many complications in overload resolution.
    try:
        iter(obj)
        return not isinstance(obj, six.string_types)
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


cdef box_sig(JNIEnv *j_env, JNIRef j_klass):
    original_sig = klass_sig(CQPEnv.wrap(j_env), j_klass)
    box_cls_name = PRIMITIVE_TYPES.get(original_sig)
    return f"Ljava/lang/{box_cls_name};" if box_cls_name else original_sig


# TODO #5170: range checking may lead to incorrect overload caching.
cdef JNIRef p2j_box(CQPEnv env, JNIRef j_klass, str box_cls_name, value):
    full_box_cls_name = "java.lang." + box_cls_name
    j_box_klass = env.FindClass(full_box_cls_name)
    if not env.IsAssignableFrom(j_box_klass, j_klass):
        return None

    if isinstance(value, java.Primitive):
        value = value.value

    # Uniquely among the boxed types, the Float class has two primitive-typed constructors, one
    # of which takes a double, which our overload resolution will prefer.
    if box_cls_name == "Float":
        check_range_float32(value)

    # This will result in a recursive call to p2j, this time requesting the primitive type of
    # the constructor parameter. Range checks will be performed by populate_args.
    return jclass(full_box_cls_name)(value)._chaquopy_this


cdef jobject p2j_pyobject(JNIEnv *env, obj) except? NULL:
    if obj is None:
        return NULL
    # Can't call getInstance() using jclass because that'll immediately unwrap the
    # returned proxy object (see j2p)
    JPyObject = jclass("com.chaquo.python.PyObject")
    cdef JavaMethod jm_getInstance = JPyObject.getInstance
    cdef jobject j_pyobject = env[0].CallStaticObjectMethod \
        (env,
         (<JNIRef?>JPyObject._chaquopy_j_klass).obj,
         jm_getInstance.j_method,
         <jlong><PyObject*>obj)
    check_exception(env)
    return j_pyobject
