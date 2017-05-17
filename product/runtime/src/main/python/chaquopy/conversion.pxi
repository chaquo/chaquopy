from cpython.version cimport PY_MAJOR_VERSION

import six
import sys

from cpython.object cimport PyObject

import chaquopy


JCHAR_ENCODING = "UTF-16-LE" if sys.byteorder == "little" else "UTF-16-BE"


cdef jstringy_arg(argtype):
    return argtype in ('Ljava/lang/String;',
                       'Ljava/lang/CharSequence;',
                       'Ljava/lang/Object;')


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
                pass
            j_env[0].DeleteLocalRef(j_env, j_args[index].l)


# Must be consistent with arg_is_applicable
cdef void populate_args(JNIEnv *j_env, tuple definition_args, jvalue *j_args, args) except *:
    # FIXME perform range and type checks, unless Cython checks and errors are adequate.
    #
    # We don't implement auto-unboxing, because the boxed types are automatically unboxed by
    # j2p and should therefore never normally be touched by Python user code. Auto-boxing, on
    # the other hand, will be done if necessary by p2j.
    cdef int index
    for index, argtype in enumerate(definition_args):
        py_arg = args[index]
        if argtype == 'Z':
            j_args[index].z = py_arg
        elif argtype == 'B':
            j_args[index].b = py_arg
        elif argtype == 'C':
            j_args[index].c = ord(py_arg)
        elif argtype == 'S':
            j_args[index].s = py_arg
        elif argtype == 'I':
            j_args[index].i = py_arg
        elif argtype == 'J':
            j_args[index].j = py_arg
        elif argtype == 'F':
            j_args[index].f = py_arg
        elif argtype == 'D':
            j_args[index].d = py_arg
        elif argtype[0] in 'L[':
            j_args[index].l = p2j(j_env, argtype, py_arg).return_ref(j_env)


# FIXME remove definition_ignored
cdef j2p(JNIEnv *j_env, definition_ignored, jobject j_object):
    if j_object == NULL:
        return None

    cdef jclass retclass
    cdef jmethodID retmeth

    r = lookup_java_object_name(j_env, j_object)

    if r[0] == '[':
        return j2p_array(j_env, r[1:], j_object)

    if r == 'java.lang.String':
        return j2p_string(j_env, j_object)
    if r == 'java.lang.Long':
        retclass = j_env[0].GetObjectClass(j_env, j_object)
        retmeth = j_env[0].GetMethodID(j_env, retclass, 'longValue', '()J')
        return j_env[0].CallLongMethod(j_env, j_object, retmeth)
    if r == 'java.lang.Integer':
        retclass = j_env[0].GetObjectClass(j_env, j_object)
        retmeth = j_env[0].GetMethodID(j_env, retclass, 'intValue', '()I')
        return j_env[0].CallIntMethod(j_env, j_object, retmeth)
    if r == 'java.lang.Float':
        retclass = j_env[0].GetObjectClass(j_env, j_object)
        retmeth = j_env[0].GetMethodID(j_env, retclass, 'floatValue', '()F')
        return j_env[0].CallFloatMethod(j_env, j_object, retmeth)
    if r == 'java.lang.Double':
        retclass = j_env[0].GetObjectClass(j_env, j_object)
        retmeth = j_env[0].GetMethodID(j_env, retclass, 'doubleValue', '()D')
        return j_env[0].CallDoubleMethod(j_env, j_object, retmeth)
    if r == 'java.lang.Short':
        retclass = j_env[0].GetObjectClass(j_env, j_object)
        retmeth = j_env[0].GetMethodID(j_env, retclass, 'shortValue', '()S')
        return j_env[0].CallShortMethod(j_env, j_object, retmeth)
    if r == 'java.lang.Boolean':
        retclass = j_env[0].GetObjectClass(j_env, j_object)
        retmeth = j_env[0].GetMethodID(j_env, retclass, 'booleanValue', '()Z')
        return j_env[0].CallBooleanMethod(j_env, j_object, retmeth)
    if r == 'java.lang.Byte':
        retclass = j_env[0].GetObjectClass(j_env, j_object)
        retmeth = j_env[0].GetMethodID(j_env, retclass, 'byteValue', '()B')
        return j_env[0].CallByteMethod(j_env, j_object, retmeth)
    if r == 'java.lang.Character':
        retclass = j_env[0].GetObjectClass(j_env, j_object)
        retmeth = j_env[0].GetMethodID(j_env, retclass, 'charValue', '()C')
        return ord(j_env[0].CallCharMethod(j_env, j_object, retmeth))
    if r == 'com.chaquo.python.PyObject':
        return j2p_pyobject(j_env, j_object)

    # Failed to convert it, so return a proxy object.
    return chaquopy.autoclass(r)(instance=GlobalRef.create(j_env, j_object))


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


cdef j2p_array(JNIEnv *j_env, definition, jobject j_object):
    cdef jboolean iscopy = 0
    cdef jboolean *j_booleans
    cdef jbyte *j_bytes
    cdef jchar *j_chars
    cdef jshort *j_shorts
    cdef jint *j_ints
    cdef jlong *j_longs
    cdef jfloat *j_floats
    cdef jdouble *j_doubles
    cdef object ret = None
    cdef jsize array_size

    cdef int i
    cdef jobject j_object_item

    if j_object == NULL:
        return None

    array_size = j_env[0].GetArrayLength(j_env, j_object)

    r = definition[0]
    if r == 'Z':
        j_booleans = j_env[0].GetBooleanArrayElements(
                j_env, j_object, &iscopy)
        ret = [(True if j_booleans[i] else False)
                for i in range(array_size)]
        j_env[0].ReleaseBooleanArrayElements(
                j_env, j_object, j_booleans, 0)

    elif r == 'B':
        j_bytes = j_env[0].GetByteArrayElements(
                j_env, j_object, &iscopy)
        # FIXME is this "unsigned" consistent with other Java byte -> Python int conversions?
        # It seems like the wrong choice.
        ret = [(<unsigned char>j_bytes[i]) for i in range(array_size)]
        j_env[0].ReleaseByteArrayElements(
                j_env, j_object, j_bytes, 0)

    elif r == 'C':
        j_chars = j_env[0].GetCharArrayElements(
                j_env, j_object, &iscopy)
        # FIXME this is suspicious, Cython char is 8 bits but Java char is 16
        ret = [chr(<char>j_chars[i]) for i in range(array_size)]
        j_env[0].ReleaseCharArrayElements(
                j_env, j_object, j_chars, 0)

    elif r == 'S':
        j_shorts = j_env[0].GetShortArrayElements(
                j_env, j_object, &iscopy)
        ret = [(<short>j_shorts[i]) for i in range(array_size)]
        j_env[0].ReleaseShortArrayElements(
                j_env, j_object, j_shorts, 0)

    elif r == 'I':
        j_ints = j_env[0].GetIntArrayElements(
                j_env, j_object, &iscopy)
        ret = [(<int>j_ints[i]) for i in range(array_size)]
        j_env[0].ReleaseIntArrayElements(
                j_env, j_object, j_ints, 0)

    elif r == 'J':
        j_longs = j_env[0].GetLongArrayElements(
                j_env, j_object, &iscopy)
        ret = [(<long long>j_longs[i]) for i in range(array_size)]
        j_env[0].ReleaseLongArrayElements(
                j_env, j_object, j_longs, 0)

    elif r == 'F':
        j_floats = j_env[0].GetFloatArrayElements(
                j_env, j_object, &iscopy)
        ret = [(<float>j_floats[i]) for i in range(array_size)]
        j_env[0].ReleaseFloatArrayElements(
                j_env, j_object, j_floats, 0)

    elif r == 'D':
        j_doubles = j_env[0].GetDoubleArrayElements(
                j_env, j_object, &iscopy)
        ret = [(<double>j_doubles[i]) for i in range(array_size)]
        j_env[0].ReleaseDoubleArrayElements(
                j_env, j_object, j_doubles, 0)

    elif r == 'L':
        r = definition[1:-1]
        ret = []
        for i in range(array_size):
            j_object_item = j_env[0].GetObjectArrayElement(
                    j_env, j_object, i)
            if j_object_item == NULL:
                ret.append(None)
                continue
            obj = j2p(j_env, definition, j_object_item)
            ret.append(obj)
            j_env[0].DeleteLocalRef(j_env, j_object_item)

    elif r == '[':
        r = definition[1:]
        ret = []
        for i in range(array_size):
            j_object_item = j_env[0].GetObjectArrayElement(
                    j_env, j_object, i)
            if j_object_item == NULL:
                ret.append(None)
                continue
            obj = j2p_array(j_env, r, j_object_item)
            ret.append(obj)
            j_env[0].DeleteLocalRef(j_env, j_object_item)

    else:
        raise JavaException('Invalid return definition for array')

    return ret


class RangeError(TypeError):
    """Indicates that a value could not be converted to the requested type because it was outside
    of the type's range.
    """
    pass


# Must be consistent with arg_is_applicable
cdef JNIRef p2j(JNIEnv *j_env, definition, obj):
    if definition[0] == 'V':
        # Could happen from proxy.pxi
        if obj is not None:
            raise TypeError("Void method cannot return a value")
        return LocalRef()

    elif definition[0] in "ZBCDFIJS":
        raise TypeError("Cannot convert to primitive type (e.g. 'int'); use the boxed type "
                        "(e.g. 'Integer') instead")

    elif definition[0] == 'L':
        clsname = definition[1:-1].replace("/", ".")
        klass = find_javaclass(clsname)

        if obj is None:
            return LocalRef()

        elif isinstance(obj, six.string_types):
            if jstringy_arg(definition):
                u = obj.decode('ASCII') if isinstance(obj, bytes) else obj
                utf16 = u.encode(JCHAR_ENCODING)
                  # len(u) doesn't necessarily equal len(utf16)//2 on a "narrow" Python
                return LocalRef.adopt(j_env, j_env[0].NewString(j_env,
                                                                <jchar*><char*>utf16,
                                                                len(utf16)//2))
            elif len(obj) == 1:
                Character = find_javaclass("java.lang.Character")
                if klass.isAssignableFrom(Character):
                    return p2j_box(j_env, Character, obj)
        elif isinstance(obj, bool):
            Boolean = find_javaclass("java.lang.Boolean")
            if klass.isAssignableFrom(Boolean):
                return p2j_box(j_env, Boolean, obj)
        elif isinstance(obj, six.integer_types):
            # Integer will be preferred if clsname is Number or Object, because that's the type
            # of an undecorated Java floating point literal.
            #
            # TODO If clsname is Number or Object, and Integer isn't big enough, try Long.
            #
            # TODO support BigInteger (#5174), and make that a final fallback if clsname is
            # Number or Object, and Long isn't big enough.
            #
            # FIXME this fails for Float because it has two constructors and more_specific
            # doesn't handle primitive types.
            #
            # FIXME this will delegate range checking to populate_args: test whether Cython
            # checks and errors are adequate. And raise RangeError (see arg_is_applicable).
            for box_clsname in ["Integer", "Long", "Short", "Byte", "Double", "Float", "Character"]:
                box_klass = find_javaclass("java.lang." + box_clsname)
                if klass.isAssignableFrom(box_klass):
                    return p2j_box(j_env, box_klass, obj)
        elif isinstance(obj, float):
            # Double will be used if clsname is Number or Object, because that's the type of an
            # undecorated Java floating point literal.
            for box_clsname in ["Double", "Float"]:
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
        elif isinstance(obj, (tuple, list)):
            if clsname == "java.lang.Object":
                return LocalRef.adopt(j_env, p2j_array(j_env, definition, obj))

        # Anything, including the above types, can be converted to a PyObject if the signature
        # will accept it.
        if klass.isAssignableFrom(find_javaclass("com.chaquo.python.PyObject")):
            return LocalRef.adopt(j_env, p2j_pyobject(j_env, obj))

    elif definition[0] == '[':
        if isinstance(obj, (tuple, list)) or \
           (isinstance(obj, bytearray) and definition == "[B"):
            return LocalRef.adopt(j_env, p2j_array(j_env, definition[1:], obj))

    else:
        raise ValueError(f"Invalid signature '{definition}'")

    raise TypeError(f"Cannot convert {type(obj).__name__} to {definition}")


cdef JNIRef p2j_string(JNIEnv *env, s):
    return p2j(env, "Ljava/lang/String;", s)


cdef LocalRef p2j_box(JNIEnv *env, box_klass, value):
    cdef JavaObject boxed = chaquopy.autoclass(box_klass.getName())(value)
    return LocalRef.create(env, boxed.j_self.obj)


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
    cdef jobject ret = NULL
    cdef int array_size = len(pyarray)
    cdef int i
    cdef jboolean j_boolean
    cdef jbyte j_byte
    cdef jchar j_char
    cdef jshort j_short
    cdef jint j_int
    cdef jlong j_long
    cdef jfloat j_float
    cdef jdouble j_double
    cdef JNIRef j_object
    cdef jclass j_class

    if pyarray is None:
        return NULL

    if definition == 'Z':
        ret = j_env[0].NewBooleanArray(j_env, array_size)
        for i in range(array_size):
            j_boolean = 1 if pyarray[i] else 0
            j_env[0].SetBooleanArrayRegion(j_env,
                    ret, i, 1, &j_boolean)

    elif definition == 'B':
        ret = j_env[0].NewByteArray(j_env, array_size)
        for i in range(array_size):
            # FIXME compare signedness with other byte conversions, and test properly
            j_byte = <jbyte><unsigned char>pyarray[i]
            j_env[0].SetByteArrayRegion(j_env,
                    ret, i, 1, &j_byte)

    elif definition == 'C':
        ret = j_env[0].NewCharArray(j_env, array_size)
        for i in range(array_size):
            j_char = ord(pyarray[i])
            j_env[0].SetCharArrayRegion(j_env,
                    ret, i, 1, &j_char)

    elif definition == 'S':
        ret = j_env[0].NewShortArray(j_env, array_size)
        for i in range(array_size):
            j_short = pyarray[i]
            j_env[0].SetShortArrayRegion(j_env,
                    ret, i, 1, &j_short)

    elif definition == 'I':
        ret = j_env[0].NewIntArray(j_env, array_size)
        for i in range(array_size):
            j_int = pyarray[i]
            j_env[0].SetIntArrayRegion(j_env,
                    ret, i, 1, <const jint *>&j_int)

    elif definition == 'J':
        ret = j_env[0].NewLongArray(j_env, array_size)
        for i in range(array_size):
            j_long = pyarray[i]
            j_env[0].SetLongArrayRegion(j_env,
                    ret, i, 1, &j_long)

    elif definition == 'F':
        ret = j_env[0].NewFloatArray(j_env, array_size)
        for i in range(array_size):
            j_float = pyarray[i]
            j_env[0].SetFloatArrayRegion(j_env,
                    ret, i, 1, &j_float)

    elif definition == 'D':
        ret = j_env[0].NewDoubleArray(j_env, array_size)
        for i in range(array_size):
            j_double = pyarray[i]
            j_env[0].SetDoubleArrayRegion(j_env,
                    ret, i, 1, &j_double)

    elif definition[0] == 'L':
        defstr = str_for_c(definition[1:-1])
        j_class = j_env[0].FindClass(j_env, <bytes>defstr)
        if j_class == NULL:
            raise JavaException('Cannot create array with a class not '
                    'found {0!r}'.format(definition[1:-1]))
        ret = j_env[0].NewObjectArray(j_env, array_size, j_class, NULL)
        for i in range(array_size):
            j_object = p2j(j_env, definition, pyarray[i])
            j_env[0].SetObjectArrayElement(j_env, ret, i, j_object.obj)

    elif definition[0] == '[':
        # FIXME shouldn't depend only on first element, and will crash when array is empty. Can
        # we combine this with the 'L' case?
        subdef = definition[1:]
        eproto = p2j_array(j_env, subdef, pyarray[0])
        ret = j_env[0].NewObjectArray(
                j_env, array_size, j_env[0].GetObjectClass(j_env, eproto), NULL)
        j_env[0].SetObjectArrayElement(
                    j_env, <jobjectArray>ret, 0, eproto)
        for i in range(1, array_size):
            j_env[0].SetObjectArrayElement(
                    j_env, <jobjectArray>ret, i, p2j_array(j_env, subdef, pyarray[i]))

    else:
        raise ValueError(f"Invalid signature '{definition}'")

    return ret
