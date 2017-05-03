from cpython.version cimport PY_MAJOR_VERSION

import sys

if sys.byteorder == "little":
    JCHAR_ENCODING = "UTF-16-LE"
else:
    JCHAR_ENCODING = "UTF-16-BE"


cdef jstringy_arg(argtype):
    return argtype in ('Ljava/lang/String;',
                       'Ljava/lang/CharSequence;',
                       'Ljava/lang/Object;')

cdef void release_args(JNIEnv *j_env, tuple definition_args, jvalue *j_args, args) except *:
    cdef int index
    for index, argtype in enumerate(definition_args):
        py_arg = args[index]
        if argtype[0] == 'L':
            if py_arg is None:
                j_args[index].l = NULL
            if isinstance(py_arg, basestring) and \
                    jstringy_arg(argtype):
                j_env[0].DeleteLocalRef(j_env, j_args[index].l)
        elif argtype[0] == '[':
            # Copy back any modifications the Java method may have made to the array
            ret = convert_jarray_to_python(j_env, argtype[1:], j_args[index].l)
            try:
                args[index][:] = ret
            except TypeError:
                pass
            j_env[0].DeleteLocalRef(j_env, j_args[index].l)

cdef void populate_args(JNIEnv *j_env, tuple definition_args, jvalue *j_args, args) except *:
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
        elif argtype[0] == 'L':
            j_args[index].l = convert_python_to_jobject(j_env, argtype, py_arg)
        elif argtype[0] == '[':
            if py_arg is None:
                j_args[index].l = NULL
                continue
            if isinstance(py_arg, basestring) and PY_MAJOR_VERSION < 3:
                if argtype == '[B':
                    py_arg = map(ord, py_arg)
                elif argtype == '[C':
                    py_arg = list(py_arg)
            if isinstance(py_arg, str) and PY_MAJOR_VERSION >= 3 and argtype == '[C':
                py_arg = list(py_arg)
            if not isinstance(py_arg, (list, tuple, bytes, bytearray)):
                raise JavaException('Expecting a python list/tuple, got '
                        '{0!r}'.format(py_arg))
            j_args[index].l = convert_pyarray_to_java(
                    j_env, argtype[1:], py_arg)


cdef convert_jobject_to_python(JNIEnv *j_env, definition, jobject j_object):
    cdef jstring string
    cdef const jchar *jchar_str
    # We can't decode directly from a jchar array because of
    # https://github.com/cython/cython/issues/1696 . This cdef is necessary to prevent Cython
    # inferring the type of bytes_str and calling the decode function directly.
    cdef object bytes_str

    r = definition[1:-1]
    cdef JavaObject ret_jc
    cdef jclass retclass
    cdef jmethodID retmeth

    # we got a generic object -> lookup for the real name instead.
    if r == 'java/lang/Object':
        r = definition = lookup_java_object_name(j_env, j_object)
        # print('cjtp:r {0} definition {1}'.format(r, definition))

    if definition[0] == '[':
        return convert_jarray_to_python(j_env, definition[1:], j_object)

    if r in ('java/lang/String', 'java/lang/CharSequence'):
        if r == 'java/lang/CharSequence':
            retclass = j_env[0].GetObjectClass(j_env, j_object)
            retmeth = j_env[0].GetMethodID(j_env, retclass, "toString", "()Ljava/lang/String;")
            string = <jstring> (j_env[0].CallObjectMethod(j_env, j_object, retmeth))
        else:
            string = <jstring>j_object
        jchar_str = j_env[0].GetStringChars(j_env, string, NULL)
        str_len = j_env[0].GetStringLength(j_env, string)
        bytes_str = (<char*>jchar_str)[:str_len * 2]  # See note at bytes_str cdef above
        j_env[0].ReleaseStringChars(j_env, string, jchar_str)
        return bytes_str.decode(JCHAR_ENCODING)

    # XXX should be deactivable from configuration
    # ie, user might not want autoconvertion of lang classes.
    if r == 'java/lang/Long':
        retclass = j_env[0].GetObjectClass(j_env, j_object)
        retmeth = j_env[0].GetMethodID(j_env, retclass, 'longValue', '()J')
        return j_env[0].CallLongMethod(j_env, j_object, retmeth)
    if r == 'java/lang/Integer':
        retclass = j_env[0].GetObjectClass(j_env, j_object)
        retmeth = j_env[0].GetMethodID(j_env, retclass, 'intValue', '()I')
        return j_env[0].CallIntMethod(j_env, j_object, retmeth)
    if r == 'java/lang/Float':
        retclass = j_env[0].GetObjectClass(j_env, j_object)
        retmeth = j_env[0].GetMethodID(j_env, retclass, 'floatValue', '()F')
        return j_env[0].CallFloatMethod(j_env, j_object, retmeth)
    if r == 'java/lang/Double':
        retclass = j_env[0].GetObjectClass(j_env, j_object)
        retmeth = j_env[0].GetMethodID(j_env, retclass, 'doubleValue', '()D')
        return j_env[0].CallDoubleMethod(j_env, j_object, retmeth)
    if r == 'java/lang/Short':
        retclass = j_env[0].GetObjectClass(j_env, j_object)
        retmeth = j_env[0].GetMethodID(j_env, retclass, 'shortValue', '()S')
        return j_env[0].CallShortMethod(j_env, j_object, retmeth)
    if r == 'java/lang/Boolean':
        retclass = j_env[0].GetObjectClass(j_env, j_object)
        retmeth = j_env[0].GetMethodID(j_env, retclass, 'booleanValue', '()Z')
        return j_env[0].CallBooleanMethod(j_env, j_object, retmeth)
    if r == 'java/lang/Byte':
        retclass = j_env[0].GetObjectClass(j_env, j_object)
        retmeth = j_env[0].GetMethodID(j_env, retclass, 'byteValue', '()B')
        return j_env[0].CallByteMethod(j_env, j_object, retmeth)
    if r == 'java/lang/Character':
        retclass = j_env[0].GetObjectClass(j_env, j_object)
        retmeth = j_env[0].GetMethodID(j_env, retclass, 'charValue', '()C')
        return ord(j_env[0].CallCharMethod(j_env, j_object, retmeth))

    if r not in jclass_register:
        if r.startswith('$Proxy'):
            # only for $Proxy on android, don't use autoclass. The dalvik vm is
            # not able to give us introspection on that one (FindClass return
            # NULL).
            from .reflect import Object
            ret_jc = Object(noinstance=True)
        else:
            from .reflect import autoclass
            ret_jc = autoclass(r.replace('/', '.'))(noinstance=True)
    else:
        ret_jc = jclass_register[r](noinstance=True)
    ret_jc.instantiate_from(GlobalRef.create(j_env, j_object))
    return ret_jc

cdef convert_jarray_to_python(JNIEnv *j_env, definition, jobject j_object):
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
            obj = convert_jobject_to_python(j_env, definition, j_object_item)
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
            obj = convert_jarray_to_python(j_env, r, j_object_item)
            ret.append(obj)
            j_env[0].DeleteLocalRef(j_env, j_object_item)

    else:
        raise JavaException('Invalid return definition for array')

    return ret

cdef jobject convert_python_to_jobject(JNIEnv *j_env, definition, obj) except *:
    cdef jobject retobject, retsubobject
    cdef jclass retclass = NULL
    cdef jmethodID retmidinit = NULL
    cdef jvalue j_ret[1]
    cdef JavaObject jc
    cdef PythonJavaClass pc
    cdef int index

    if definition[0] == 'V':
        return NULL
    elif definition[0] == 'L':
        if obj is None:
            return NULL
        elif isinstance(obj, (unicode, bytes)) and jstringy_arg(definition):
            if isinstance(obj, unicode):
                utf16 = obj.encode(JCHAR_ENCODING)
            else:
                utf16 = obj.decode('ASCII').encode(JCHAR_ENCODING)
            return j_env[0].NewString(j_env, <jchar*><char*>utf16,
                                      len(utf16)/2)  # Not equal to len(obj) on a "narrow" Python
        elif isinstance(obj, (int, long)) and \
                definition in (
                    'Ljava/lang/Integer;',
                    'Ljava/lang/Number;',
                    'Ljava/lang/Long;',
                    'Ljava/lang/Object;'):
            # FIXME this isn't right, it could pass a Long where an Integer is required. And it
            # needs to support all the other boxed types properly as well.
            j_ret[0].i = obj
            retclass = j_env[0].FindClass(j_env, 'java/lang/Integer')
            retmidinit = j_env[0].GetMethodID(j_env, retclass, '<init>', '(I)V')
            retobject = j_env[0].NewObjectA(j_env, retclass, retmidinit, j_ret)
            return retobject
        elif isinstance(obj, JavaObject):
            jc = obj
            check_assignable_from(j_env, jc, definition[1:-1])
            return jc.j_self.obj
        elif isinstance(obj, JavaClass):
            return (<GlobalRef?>obj.j_cls).obj
        elif isinstance(obj, PythonJavaClass):
            pc = obj
            jc = pc.j_self
            return jc.j_self.obj
        elif isinstance(obj, (tuple, list)):
            return convert_pyarray_to_java(j_env, definition, obj)
        else:
            raise JavaException('Invalid python object for this '
                    'argument. Want {0!r}, got {1!r}'.format(
                        definition[1:-1], obj))

    elif definition[0] == '[':
        if PY_MAJOR_VERSION < 3:
            conversions = {
                int: 'I',
                bool: 'Z',
                long: 'J',
                float: 'F',
                basestring: 'Ljava/lang/String;',
            }
        else:
            conversions = {
                int: 'I',
                bool: 'Z',
                long: 'J',
                float: 'F',
                str: 'Ljava/lang/String;',
                bytes: 'B'
            }
        retclass = j_env[0].FindClass(j_env, 'java/lang/Object')
        retobject = j_env[0].NewObjectArray(j_env, len(obj), retclass, NULL)
        for index, item in enumerate(obj):
            item_definition = conversions.get(type(item), definition[1:])
            retsubobject = convert_python_to_jobject(
                    j_env, item_definition, item)
            j_env[0].SetObjectArrayElement(j_env, retobject, index,
                    retsubobject)
        return retobject

    elif definition == 'B':
        retclass = j_env[0].FindClass(j_env, 'java/lang/Byte')
        retmidinit = j_env[0].GetMethodID(j_env, retclass, '<init>', '(B)V')
        j_ret[0].b = obj
    elif definition == 'S':
        retclass = j_env[0].FindClass(j_env, 'java/lang/Short')
        retmidinit = j_env[0].GetMethodID(j_env, retclass, '<init>', '(S)V')
        j_ret[0].s = obj
    elif definition == 'I':
        retclass = j_env[0].FindClass(j_env, 'java/lang/Integer')
        retmidinit = j_env[0].GetMethodID(j_env, retclass, '<init>', '(I)V')
        j_ret[0].i = int(obj)
    elif definition == 'J':
        retclass = j_env[0].FindClass(j_env, 'java/lang/Long')
        retmidinit = j_env[0].GetMethodID(j_env, retclass, '<init>', '(J)V')
        j_ret[0].j = obj
    elif definition == 'F':
        retclass = j_env[0].FindClass(j_env, 'java/lang/Float')
        retmidinit = j_env[0].GetMethodID(j_env, retclass, '<init>', '(F)V')
        j_ret[0].f = obj
    elif definition == 'D':
        retclass = j_env[0].FindClass(j_env, 'java/lang/Double')
        retmidinit = j_env[0].GetMethodID(j_env, retclass, '<init>', '(D)V')
        j_ret[0].d = obj
    elif definition == 'C':
        retclass = j_env[0].FindClass(j_env, 'java/lang/Char')
        retmidinit = j_env[0].GetMethodID(j_env, retclass, '<init>', '(C)V')
        j_ret[0].c = ord(obj)
    elif definition == 'Z':
        retclass = j_env[0].FindClass(j_env, 'java/lang/Boolean')
        retmidinit = j_env[0].GetMethodID(j_env, retclass, '<init>', '(Z)V')
        j_ret[0].z = 1 if obj else 0
    else:
        raise ValueError(f"Invalid definition {definition}")

    if retclass == NULL:
        raise ValueError(f"FindClass failed in convert_python_to_jobject")

    # XXX do we need a globalref or something ?
    retobject = j_env[0].NewObjectA(j_env, retclass, retmidinit, j_ret)
    return retobject


cdef jobject convert_pyarray_to_java(JNIEnv *j_env, definition, pyarray) except *:
    cdef jarray ret = NULL
    cdef int array_size = len(pyarray)
    cdef int i
    cdef unsigned char c_tmp
    cdef jboolean j_boolean
    cdef jbyte j_byte
    cdef jchar j_char
    cdef jshort j_short
    cdef jint j_int
    cdef jlong j_long
    cdef jfloat j_float
    cdef jdouble j_double
    cdef jclass j_class

    if definition == 'Ljava/lang/Object;' and len(pyarray) > 0:
        # then the method will accept any array type as param
        # let's be as precise as we can
        if PY_MAJOR_VERSION < 3:
            conversions = {
                int: 'I',
                bool: 'Z',
                long: 'J',
                float: 'F',
                basestring: 'Ljava/lang/String;',
            }
        else:
            conversions = {
                int: 'I',
                bool: 'Z',
                long: 'J',
                float: 'F',
                bytes: 'B',
                str: 'Ljava/lang/String;',
            }
        for _type, override in conversions.iteritems():
            if isinstance(pyarray[0], _type):
                definition = override
                break

    if definition == 'Z':
        ret = j_env[0].NewBooleanArray(j_env, array_size)
        for i in range(array_size):
            j_boolean = 1 if pyarray[i] else 0
            j_env[0].SetBooleanArrayRegion(j_env,
                    ret, i, 1, &j_boolean)

    elif definition == 'B':
        ret = j_env[0].NewByteArray(j_env, array_size)
        for i in range(array_size):
            # FIXME why the tmp?
            c_tmp = pyarray[i]
            j_byte = <signed char>c_tmp
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
            j_env[0].SetObjectArrayElement(j_env, ret, i,
                                           convert_python_to_jobject(j_env, definition, pyarray[i]))

    elif definition[0] == '[':
        subdef = definition[1:]
        eproto = convert_pyarray_to_java(j_env, subdef, pyarray[0])
        ret = j_env[0].NewObjectArray(
                j_env, array_size, j_env[0].GetObjectClass(j_env, eproto), NULL)
        j_env[0].SetObjectArrayElement(
                    j_env, <jobjectArray>ret, 0, eproto)
        for i in range(1, array_size):
            j_env[0].SetObjectArrayElement(
                    j_env, <jobjectArray>ret, i, convert_pyarray_to_java(j_env, subdef, pyarray[i]))

    else:
        raise JavaException('Invalid array definition', definition, pyarray)

    return <jobject>ret
