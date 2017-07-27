from cpython.version cimport PY_MAJOR_VERSION

from collections import OrderedDict
import re
import sys

from cpython.object cimport PyObject
from libc.float cimport FLT_MAX


INT_TYPES = "BSIJ"                          # Order matters: see is_assignable_from.
FLOAT_TYPES = "FD"                          #   "      "
NUMERIC_TYPES = INT_TYPES + FLOAT_TYPES     #   "      "
PRIMITIVE_TYPES = NUMERIC_TYPES + "CZ"      # Order doesn't matter here.

# In order of preference when assigning to a Number or Object.
BOXED_INT_TYPES = OrderedDict([("J", "Long"), ("I", "Integer"), ("S", "Short"), ("B", "Byte")])
BOXED_FLOAT_TYPES = OrderedDict([("D", "Double"), ("F", "Float")])
BOXED_NUMERIC_TYPES = OrderedDict(list(BOXED_INT_TYPES.items()) + list(BOXED_FLOAT_TYPES.items()))

UNBOX_METHODS = {f"java.lang.{boxed}": f"{unboxed}Value" for boxed, unboxed in
                 [("Boolean", "boolean"), ("Byte", "byte"), ("Short", "short"), ("Integer", "int"),
                  ("Long", "long"), ("Float", "float"), ("Double", "double"), ("Character", "char")]}

ARRAY_CONVERSIONS = ["Ljava/lang/Object;", "Ljava/lang/Cloneable;", "Ljava/io/Serializable;"]

JCHAR_ENCODING = "UTF-16-LE" if sys.byteorder == "little" else "UTF-16-BE"


# Copy back any modifications the Java method may have made to mutable parameters.
def copy_output_args(definition_args, args, p2j_args):
    for index, argtype in enumerate(definition_args):
        if argtype[0] == "[" and not isinstance(args[index], JavaArray):
            ret = java.jarray(argtype[1:])(instance=p2j_args[index])
            try:
                args[index][:] = ret
            except TypeError:
                pass    # The arg was a tuple or other read-only sequence.


# Cython auto-generates range checking code for the integral types.
cdef populate_args(JNIEnv *j_env, tuple definition_args, jvalue *j_args, args):
    for index, argtype in enumerate(definition_args):
        py_arg = args[index]
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

    r = lookup_java_object_name(j_env, j_object.obj)
    if r[0] == '[':
        return java.jarray(r[1:])(instance=j_object)
    if r == 'java.lang.String':
        return j2p_string(j_env, j_object.obj)

    unbox_method = UNBOX_METHODS.get(r)
    if unbox_method:
        return getattr(java.jclass(r)(instance=j_object), unbox_method)()

    if r == 'com.chaquo.python.PyObject':
        return j2p_pyobject(j_env, j_object.obj)

    # Failed to convert it, so return a proxy object.
    return java.jclass(r)(instance=j_object)


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
                                 (<JNIRef?>find_javaclass("java.lang.String")._chaquopy_this).obj):
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
    JPyObject = java.jclass("com.chaquo.python.PyObject")
    jpo = JPyObject(instance=GlobalRef.create(env, jpyobject))
    cdef PyObject *po = <PyObject*><jlong> jpo.addr
    if po == NULL:
        raise ValueError("PyObject is closed")
    return <object>po


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
    # We don't do auto-unboxing here, because boxed types are automatically unboxed by
    # j2p and should therefore never normally be touched by Python user code. Auto-boxing, on
    # the other hand, will be done if necessary below.
    elif definition in PRIMITIVE_TYPES:
        if definition == 'Z':
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
               INT_TYPES.find(obj.sig) <= INT_TYPES.find(definition):
                return obj.value

        elif definition in FLOAT_TYPES:
            if isinstance(obj, (float, six.integer_types)) and not isinstance(obj, bool):
                return obj
            if isinstance(obj, java.NumericPrimitive) and \
               NUMERIC_TYPES.find(obj.sig) <= NUMERIC_TYPES.find(definition):
                return obj.value

        elif definition == "C":
            # We don't check that len(obj) == 1; see note above about range checks.
            if isinstance(obj, six.string_types):
                return obj
            if isinstance(obj, java.jchar):
                return obj.value

        else:
            raise Exception(f"Unknown primitive type {definition}")

    elif definition[0] == 'L':
        clsname = definition[1:-1].replace("/", ".")
        klass = find_javaclass(clsname)

        if obj is None:
            return LocalRef()
        elif isinstance(obj, NoneCast):
            if klass.isAssignableFrom(find_javaclass(obj.sig)):
                return LocalRef()

        elif isinstance(obj, (six.string_types, java.jchar)):
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

        elif isinstance(obj, (bool, java.jboolean)):
            if autobox:
                Boolean = find_javaclass("java.lang.Boolean")
                if klass.isAssignableFrom(Boolean):
                    return p2j_box(j_env, Boolean, obj)
        elif isinstance(obj, (six.integer_types, java.IntPrimitive)):
            if autobox:
                # TODO #5174 support BigInteger, and make that a final fallback if clsname is
                # Number or Object, and Long isn't big enough.
                #
                # Automatic primitive conversion cannot be combined with autoboxing (JLS 5.3).
                box_clsnames = ([BOXED_NUMERIC_TYPES[obj.sig]] if isinstance(obj, java.IntPrimitive)
                                else BOXED_NUMERIC_TYPES.values())
                for box_clsname in box_clsnames:
                    box_klass = find_javaclass("java.lang." + box_clsname)
                    if klass.isAssignableFrom(box_klass):
                        return p2j_box(j_env, box_klass, obj)
        elif isinstance(obj, (float, java.FloatPrimitive)):
            if autobox:
                # Automatic primitive conversion cannot be combined with autoboxing (JLS 5.3).
                box_clsnames = ([BOXED_FLOAT_TYPES[obj.sig]] if isinstance(obj, java.FloatPrimitive)
                                else BOXED_FLOAT_TYPES.values())
                for box_clsname in box_clsnames:
                    box_klass = find_javaclass("java.lang." + box_clsname)
                    if klass.isAssignableFrom(box_klass):
                        return p2j_box(j_env, box_klass, obj)

        elif isinstance(obj, JavaObject):
            if j_env[0].IsAssignableFrom(j_env, (<JNIRef?>type(obj)._chaquopy_j_klass).obj,
                                         (<JNIRef?>klass._chaquopy_this).obj):
                return obj._chaquopy_this
        elif isinstance(obj, JavaClass):
            if klass.isAssignableFrom(Class.getClass()):
                return <JNIRef?>obj._chaquopy_j_klass
        elif assignable_to_array(definition, obj):  # Can only be via ARRAY_CONVERSIONS
            return p2j_array("Ljava/lang/Object;", obj)

        # Anything, including the above types, can be converted to a PyObject if the signature
        # will accept it.
        elif klass.isAssignableFrom(find_javaclass("com.chaquo.python.PyObject")):
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
        return find_javaclass(definition).isAssignableFrom(find_javaclass(obj.sig))

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
        java_array = java.jarray(element_type)(obj)
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


cdef JNIRef p2j_box(JNIEnv *env, box_klass, value):
    if isinstance(value, java.Primitive):
        value = value.value

    # Uniquely among the boxed types, the Float class has two primitive-typed constructors, one
    # of which takes a double, which our overload resolution will prefer.
    clsname = box_klass.getName()
    if clsname == "java.lang.Float":
        check_range_float32(value)

    # This will result in a recursive call to p2j, this time requesting the primitive type of
    # the constructor parameter. Range checks will be performed by populate_args.
    return java.jclass(clsname)(value)._chaquopy_this


cdef jobject p2j_pyobject(JNIEnv *env, obj) except *:
    if obj is None:
        return NULL
    # Can't call getInstance() using jclass because that'll immediately unwrap the
    # returned proxy object (see j2p)
    JPyObject = java.jclass("com.chaquo.python.PyObject")
    cdef JavaMethod jm_getInstance = JPyObject.__dict__["getInstance"]
    jm_getInstance.resolve()
    cdef jobject j_pyobject = env[0].CallStaticObjectMethod \
        (env,
         (<JNIRef?>JPyObject._chaquopy_j_klass).obj,
         jm_getInstance.j_method,
         <jlong><PyObject*>obj)
    check_exception(env)
    return j_pyobject
