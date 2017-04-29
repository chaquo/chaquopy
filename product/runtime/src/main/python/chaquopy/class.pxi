import six

class JavaException(Exception):
    # TODO: should only be used for real Java exceptions, use standard Python exceptions for
    # internal errors.

    classname = None     # The classname of the exception
    innermessage = None  # The message of the inner exception
    stacktrace = None    # The stack trace of the inner exception

    def __init__(self, message, classname=None, innermessage=None, stacktrace=None):
        self.classname = classname
        self.innermessage = innermessage
        self.stacktrace = stacktrace
        Exception.__init__(self, message)


cdef dict jclass_register = {}

# TODO MetaJavaClass should be called JavaClass, while JavaClass should be called JavaObject.
#
# TODO override setattr on both class and object so that assignment to nonexistent fields
# doesn't just create a new __dict__ entry.
#
# cdef'ed metaclasses don't work with six's with_metaclass (https://trac.sagemath.org/ticket/18503)
class MetaJavaClass(type):
    def __init__(cls, classname, bases, classDict):
        cdef JNIEnv *j_env = get_jnienv()
        cls.__javaclass__ = str_for_c(cls.__javaclass__)
        cls.j_cls = LocalActualRef.create \
            (j_env, j_env[0].FindClass(j_env, cls.__javaclass__)).global_ref()
        if not cls.j_cls:
            raise ValueError(f"FindClass failed for {cls.__javaclass__}")

        for name, value in six.iteritems(classDict):
            if isinstance(value, JavaMember):
                value.set_resolve_info(cls, str_for_c(name))

        jclass_register[cls.__javaclass__] = cls

    @staticmethod
    def get_javaclass(name):
        return jclass_register.get(name)


# TODO special-case getClass so it can be called with or without an instance (can't support
# .class syntax because that's a reserved word).
cdef class JavaClass(object):
    '''Base class for Python -> Java proxy classes'''

    # Member variables declared in .pxd

    def __init__(self, *args, **kwargs):
        super(JavaClass, self).__init__()
        if 'noinstance' not in kwargs:
            self.call_constructor(args)

    cdef void instantiate_from(self, LocalRef j_self) except *:
        self.j_self = j_self

    # TODO merge duplicate parts with JavaMultipleMethod
    cdef void call_constructor(self, args) except *:
        # the goal is to find the class constructor, and call it with the
        # correct arguments.
        cdef jvalue *j_args = NULL
        cdef jobject j_self = NULL
        cdef jmethodID constructor = NULL
        cdef JNIEnv *j_env = get_jnienv()

        # get the constructor definition if exist
        definitions = [('()V', False)]
        if hasattr(self, '__javaconstructor__'):
            definitions = self.__javaconstructor__
        if isinstance(definitions, basestring):
            definitions = [definitions]

        if len(definitions) == 0:
            raise JavaException('No constructor available')

        elif len(definitions) == 1:
            definition, is_varargs = definitions[0]
            d_ret, d_args = parse_definition(definition)

            if is_varargs:
                args_ = args[:len(d_args) - 1] + (args[len(d_args) - 1:],)
            else:
                args_ = args
            if len(args or ()) != len(d_args or ()):
                raise JavaException('Invalid call, number of argument'
                        ' mismatch for constructor')
        else:
            scores = []
            for definition, is_varargs in definitions:
                d_ret, d_args = parse_definition(definition)
                if is_varargs:
                    args_ = args[:len(d_args) - 1] + (args[len(d_args) - 1:],)
                else:
                    args_ = args

                score = calculate_score(d_args, args)
                if score == -1:
                    continue
                scores.append((score, definition, d_ret, d_args, args_))
            if not scores:
                raise JavaException('No constructor matching your arguments')
            scores.sort()
            score, definition, d_ret, d_args, args_ = scores[-1]

        try:
            # convert python arguments to java arguments
            if len(args):
                j_args = <jvalue *>malloc(sizeof(jvalue) * len(d_args))
                if j_args == NULL:
                    raise MemoryError('Unable to allocate memory for java args')
                populate_args(j_env, d_args, j_args, args_)

            # get the java constructor
            defstr = str_for_c(definition)
            constructor = j_env[0].GetMethodID(
                j_env, (<LocalRef?>self.j_cls).obj, '<init>', defstr)
            if constructor == NULL:
                raise JavaException(f'Constructor GetMethodID failed for {self} {defstr}')

            # create the object
            j_self = j_env[0].NewObjectA(j_env, (<LocalRef?>self.j_cls).obj,
                    constructor, j_args)

            # release our arguments
            release_args(j_env, d_args, j_args, args_)

            check_exception(j_env)
            if j_self == NULL:
                raise JavaException('Unable to instantiate {0}'.format(
                    self.__javaclass__))

            self.j_self = LocalRef.create(j_env, j_self)
            j_env[0].DeleteLocalRef(j_env, j_self)
        finally:
            if j_args != NULL:
                free(j_args)

    def __repr__(self):
        return '<{0} at 0x{1:x} jclass={2} jself={3}>'.format(
                self.__class__.__name__,
                id(self),
                self.__javaclass__,
                self.j_self)


cdef class JavaMember(object):
    # Member variables declared in .pxd

    def __init__(self, bint static=False):
        self.is_static = static

    def classname(self):
        return self.jc.__javaclass__ if self.jc else None

    def set_resolve_info(self, jc, name):
        self.jc = jc
        self.name = name


cdef class JavaField(JavaMember):
    # Member variables declared in .pxd

    def __repr__(self):
        return (f"<JavaField {'static ' if self.is_static else ''}{self.definition} "
                f"{self.classname()}.{self.name}>")

    def __init__(self, definition, *, bint static=False):
        super(JavaField, self).__init__(static)
        self.definition = str_for_c(definition)

    cdef void ensure_field(self) except *:
        cdef JNIEnv *j_env = get_jnienv()
        if self.j_field != NULL:
            return
        if self.is_static:
            self.j_field = j_env[0].GetStaticFieldID(
                    j_env, (<LocalRef?>self.jc.j_cls).obj, self.name, self.definition)
        else:
            self.j_field = j_env[0].GetFieldID(
                    j_env, (<LocalRef?>self.jc.j_cls).obj, self.name, self.definition)
        if self.j_field == NULL:
            raise AttributeError(f'Get[Static]Field failed for {self}')

    def __get__(self, obj, objtype):
        cdef jobject j_self
        self.ensure_field()
        if self.is_static:
            return self.read_static_field()
        else:
            if obj is None:
                raise AttributeError(f'Cannot access {self} in static context')
            j_self = (<JavaClass?>obj).j_self.obj
            return self.read_field(j_self)

    def __set__(self, obj, value):
        cdef jobject j_self
        self.ensure_field()
        if obj is None:
            # FIXME obj will never be None: when setting a class attribute, it will simply be
            # be rebound without calling __set__. This has to be done as described at
            # http://stackoverflow.com/a/28403562/220765, or by overriding __setattr__ in the
            # metaclass so that we will actually be called with obj == None. No need to define
            # __set__ on methods, just make __setattr__ raise an exception for them.
            if not self.is_static:
                raise AttributeError(f'Cannot access {self} in static context')
            raise NotImplementedError()  # FIXME
        else:
            j_self = (<JavaClass?>obj).j_self.obj
            self.write_field(j_self, value)

    cdef write_field(self, jobject j_self, value):
        cdef jboolean j_boolean
        cdef jbyte j_byte
        cdef jchar j_char
        cdef jshort j_short
        cdef jint j_int
        cdef jlong j_long
        cdef jfloat j_float
        cdef jdouble j_double
        cdef jobject j_object
        cdef JNIEnv *j_env = get_jnienv()

        r = self.definition[0]
        if r == 'Z':
            j_boolean = <jboolean>value
            j_env[0].SetBooleanField(j_env, j_self, self.j_field, j_boolean)
        elif r == 'B':
            j_byte = <jbyte>value
            j_env[0].SetByteField(j_env, j_self, self.j_field, j_byte)
        elif r == 'C':
            j_char = <jchar>value
            j_env[0].SetCharField(j_env, j_self, self.j_field, j_char)
        elif r == 'S':
            j_short = <jshort>value
            j_env[0].SetShortField(j_env, j_self, self.j_field, j_short)
        elif r == 'I':
            j_int = <jint>value
            j_env[0].SetIntField(j_env, j_self, self.j_field, j_int)
        elif r == 'J':
            j_long = <jlong>value
            j_env[0].SetLongField(j_env, j_self, self.j_field, j_long)
        elif r == 'F':
            j_float = <jfloat>value
            j_env[0].SetFloatField(j_env, j_self, self.j_field, j_float)
        elif r == 'D':
            j_double = <jdouble>value
            j_env[0].SetDoubleField(j_env, j_self, self.j_field, j_double)
        elif r == 'L':
            j_object = <jobject>convert_python_to_jobject(j_env, self.definition, value)
            j_env[0].SetObjectField(j_env, j_self, self.j_field, j_object)
            j_env[0].DeleteLocalRef(j_env, j_object)
        else:
            raise Exception(f'Invalid field definition for {self}')

        check_exception(j_env)

    cdef read_field(self, jobject j_self):
        cdef jboolean j_boolean
        cdef jbyte j_byte
        cdef jchar j_char
        cdef jshort j_short
        cdef jint j_int
        cdef jlong j_long
        cdef jfloat j_float
        cdef jdouble j_double
        cdef jobject j_object
        cdef object ret = None
        cdef JNIEnv *j_env = get_jnienv()

        r = self.definition[0]
        if r == 'Z':
            j_boolean = j_env[0].GetBooleanField(
                    j_env, j_self, self.j_field)
            ret = True if j_boolean else False
        elif r == 'B':
            j_byte = j_env[0].GetByteField(
                    j_env, j_self, self.j_field)
            ret = <char>j_byte
        elif r == 'C':
            j_char = j_env[0].GetCharField(
                    j_env, j_self, self.j_field)
            ret = chr(<char>j_char)
        elif r == 'S':
            j_short = j_env[0].GetShortField(
                    j_env, j_self, self.j_field)
            ret = <short>j_short
        elif r == 'I':
            j_int = j_env[0].GetIntField(
                    j_env, j_self, self.j_field)
            ret = <int>j_int
        elif r == 'J':
            j_long = j_env[0].GetLongField(
                    j_env, j_self, self.j_field)
            ret = <long long>j_long
        elif r == 'F':
            j_float = j_env[0].GetFloatField(
                    j_env, j_self, self.j_field)
            ret = <float>j_float
        elif r == 'D':
            j_double = j_env[0].GetDoubleField(
                    j_env, j_self, self.j_field)
            ret = <double>j_double
        elif r == 'L':
            j_object = j_env[0].GetObjectField(
                    j_env, j_self, self.j_field)
            check_exception(j_env)
            if j_object != NULL:
                ret = convert_jobject_to_python(
                        j_env, self.definition, j_object)
                j_env[0].DeleteLocalRef(j_env, j_object)
        elif r == '[':
            r = self.definition[1:]
            j_object = j_env[0].GetObjectField(
                    j_env, j_self, self.j_field)
            check_exception(j_env)
            if j_object != NULL:
                ret = convert_jarray_to_python(j_env, r, j_object)
                j_env[0].DeleteLocalRef(j_env, j_object)
        else:
            raise Exception(f'Invalid field definition for {self}')

        check_exception(j_env)
        return ret

    cdef read_static_field(self):
        cdef jclass j_class = (<LocalRef?>self.jc.j_cls).obj
        cdef jboolean j_boolean
        cdef jbyte j_byte
        cdef jchar j_char
        cdef jshort j_short
        cdef jint j_int
        cdef jlong j_long
        cdef jfloat j_float
        cdef jdouble j_double
        cdef jobject j_object
        cdef object ret = None
        cdef JNIEnv *j_env = get_jnienv()

        r = self.definition[0]
        if r == 'Z':
            j_boolean = j_env[0].GetStaticBooleanField(
                    j_env, j_class, self.j_field)
            ret = True if j_boolean else False
        elif r == 'B':
            j_byte = j_env[0].GetStaticByteField(
                    j_env, j_class, self.j_field)
            ret = <char>j_byte
        elif r == 'C':
            j_char = j_env[0].GetStaticCharField(
                    j_env, j_class, self.j_field)
            ret = chr(<char>j_char)
        elif r == 'S':
            j_short = j_env[0].GetStaticShortField(
                    j_env, j_class, self.j_field)
            ret = <short>j_short
        elif r == 'I':
            j_int = j_env[0].GetStaticIntField(
                    j_env, j_class, self.j_field)
            ret = <int>j_int
        elif r == 'J':
            j_long = j_env[0].GetStaticLongField(
                    j_env, j_class, self.j_field)
            ret = <long long>j_long
        elif r == 'F':
            j_float = j_env[0].GetStaticFloatField(
                    j_env, j_class, self.j_field)
            ret = <float>j_float
        elif r == 'D':
            j_double = j_env[0].GetStaticDoubleField(
                    j_env, j_class, self.j_field)
            ret = <double>j_double
        elif r == 'L':
            j_object = j_env[0].GetStaticObjectField(
                    j_env, j_class, self.j_field)
            check_exception(j_env)
            if j_object != NULL:
                ret = convert_jobject_to_python(
                        j_env, self.definition, j_object)
                j_env[0].DeleteLocalRef(j_env, j_object)
        elif r == '[':
            r = self.definition[1:]
            j_object = j_env[0].GetStaticObjectField(
                    j_env, j_class, self.j_field)
            check_exception(j_env)
            if j_object != NULL:
                ret = convert_jarray_to_python(j_env, r, j_object)
                j_env[0].DeleteLocalRef(j_env, j_object)
        else:
            raise Exception(f"{self}: invalid type definition '{self.definition}'")

        check_exception(j_env)
        return ret


cdef class JavaMethod(JavaMember):
    cdef jmethodID j_method
    cdef definition
    cdef object definition_return
    cdef object definition_args
    cdef bint is_varargs

    def __repr__(self):
        return (f"<JavaMethod {'static ' if self.is_static else ''}{self.definition_return} "
                f"{self.classname()}.{self.name}{self.definition_args}>")

    def __init__(self, definition, *, bint static=False, bint varargs=False):
        super(JavaMethod, self).__init__(static)
        self.definition = str_for_c(definition)
        self.definition_return, self.definition_args = \
                parse_definition(definition)
        self.is_varargs = varargs

    cdef void ensure_method(self) except *:
        if self.j_method != NULL:
            return
        cdef JNIEnv *j_env = get_jnienv()
        if self.name is None:
            raise JavaException('Unable to find a None method!')
        if self.is_static:
            self.j_method = j_env[0].GetStaticMethodID(
                    j_env, (<LocalRef?>self.jc.j_cls).obj, self.name, self.definition)
        else:
            self.j_method = j_env[0].GetMethodID(
                    j_env, (<LocalRef?>self.jc.j_cls).obj, self.name, self.definition)

        if self.j_method == NULL:
            raise AttributeError(f"Get[Static]Method failed for {self}")

    def __get__(self, obj, objtype):
        self.ensure_method()
        if obj is None and not self.is_static:
            return self  # Unbound method: takes obj as first argument
        else:
            return lambda *args: self(obj, *args)

    def __call__(self, obj, *args):
        cdef jvalue *j_args = NULL
        cdef tuple d_args = self.definition_args
        cdef JNIEnv *j_env = get_jnienv()

        if not self.is_static and not isinstance(obj, self.jc):
            raise TypeError(f"Unbound method {self} must be called with "
                            f"{self.jc.__name__} instance as first argument (got "
                            f"{type(obj).__name__} instance instead)")

        if self.is_varargs:
            args = args[:len(d_args) - 1] + (args[len(d_args) - 1:],)

        if len(args) != len(d_args):
            raise TypeError(f'{self} takes {len(d_args)} arguments ({len(args)} given)')

        try:
            if len(args):
                j_args = <jvalue *>malloc(sizeof(jvalue) * len(d_args))
                if j_args == NULL:
                    raise MemoryError('Unable to allocate memory for java args')
                populate_args(j_env, self.definition_args, j_args, args)

            try:
                if self.is_static:
                    return self.call_staticmethod(j_env, j_args)
                else:
                    return self.call_method(j_env, obj, j_args)
            finally:
                release_args(j_env, self.definition_args, j_args, args)

        finally:
            if j_args != NULL:
                free(j_args)

    cdef call_method(self, JNIEnv *j_env, JavaClass obj, jvalue *j_args):
        cdef jboolean j_boolean
        cdef jbyte j_byte
        cdef jchar j_char
        cdef jshort j_short
        cdef jint j_int
        cdef jlong j_long
        cdef jfloat j_float
        cdef jdouble j_double
        cdef jobject j_object
        cdef object ret = None
        cdef jobject j_self = obj.j_self.obj

        r = self.definition_return[0]
        if r == 'V':
            with nogil:
                j_env[0].CallVoidMethodA(
                        j_env, j_self, self.j_method, j_args)
        elif r == 'Z':
            with nogil:
                j_boolean = j_env[0].CallBooleanMethodA(
                        j_env, j_self, self.j_method, j_args)
            ret = True if j_boolean else False
        elif r == 'B':
            with nogil:
                j_byte = j_env[0].CallByteMethodA(
                        j_env, j_self, self.j_method, j_args)
            ret = <char>j_byte
        elif r == 'C':
            with nogil:
                j_char = j_env[0].CallCharMethodA(
                        j_env, j_self, self.j_method, j_args)
            ret = chr(<char>j_char)
        elif r == 'S':
            with nogil:
                j_short = j_env[0].CallShortMethodA(
                        j_env, j_self, self.j_method, j_args)
            ret = <short>j_short
        elif r == 'I':
            with nogil:
                j_int = j_env[0].CallIntMethodA(
                        j_env, j_self, self.j_method, j_args)
            ret = <int>j_int
        elif r == 'J':
            with nogil:
                j_long = j_env[0].CallLongMethodA(
                        j_env, j_self, self.j_method, j_args)
            ret = <long long>j_long
        elif r == 'F':
            with nogil:
                j_float = j_env[0].CallFloatMethodA(
                        j_env, j_self, self.j_method, j_args)
            ret = <float>j_float
        elif r == 'D':
            with nogil:
                j_double = j_env[0].CallDoubleMethodA(
                        j_env, j_self, self.j_method, j_args)
            ret = <double>j_double
        elif r == 'L':
            with nogil:
                j_object = j_env[0].CallObjectMethodA(
                        j_env, j_self, self.j_method, j_args)
            check_exception(j_env)
            if j_object != NULL:
                ret = convert_jobject_to_python(
                        j_env, self.definition_return, j_object)
                j_env[0].DeleteLocalRef(j_env, j_object)
        elif r == '[':
            r = self.definition_return[1:]
            with nogil:
                j_object = j_env[0].CallObjectMethodA(
                        j_env, j_self, self.j_method, j_args)
            check_exception(j_env)
            if j_object != NULL:
                ret = convert_jarray_to_python(j_env, r, j_object)
                j_env[0].DeleteLocalRef(j_env, j_object)
        else:
            raise Exception('Invalid return definition?')

        check_exception(j_env)
        return ret

    cdef call_staticmethod(self, JNIEnv *j_env, jvalue *j_args):
        cdef jclass j_class = (<LocalRef?>self.jc.j_cls).obj
        cdef jboolean j_boolean
        cdef jbyte j_byte
        cdef jchar j_char
        cdef jshort j_short
        cdef jint j_int
        cdef jlong j_long
        cdef jfloat j_float
        cdef jdouble j_double
        cdef jobject j_object
        cdef object ret = None

        # return type of the java method
        r = self.definition_return[0]

        # now call the java method
        if r == 'V':
            with nogil:
                j_env[0].CallStaticVoidMethodA(
                        j_env, j_class, self.j_method, j_args)
        elif r == 'Z':
            with nogil:
                j_boolean = j_env[0].CallStaticBooleanMethodA(
                        j_env, j_class, self.j_method, j_args)
            ret = True if j_boolean else False
        elif r == 'B':
            with nogil:
                j_byte = j_env[0].CallStaticByteMethodA(
                        j_env, j_class, self.j_method, j_args)
            ret = <char>j_byte
        elif r == 'C':
            with nogil:
                j_char = j_env[0].CallStaticCharMethodA(
                        j_env, j_class, self.j_method, j_args)
            ret = chr(<char>j_char)
        elif r == 'S':
            with nogil:
                j_short = j_env[0].CallStaticShortMethodA(
                        j_env, j_class, self.j_method, j_args)
            ret = <short>j_short
        elif r == 'I':
            with nogil:
                j_int = j_env[0].CallStaticIntMethodA(
                        j_env, j_class, self.j_method, j_args)
            ret = <int>j_int
        elif r == 'J':
            with nogil:
                j_long = j_env[0].CallStaticLongMethodA(
                        j_env, j_class, self.j_method, j_args)
            ret = <long long>j_long
        elif r == 'F':
            with nogil:
                j_float = j_env[0].CallStaticFloatMethodA(
                        j_env, j_class, self.j_method, j_args)
            ret = <float>j_float
        elif r == 'D':
            with nogil:
                j_double = j_env[0].CallStaticDoubleMethodA(
                        j_env, j_class, self.j_method, j_args)
            ret = <double>j_double
        elif r == 'L':
            with nogil:
                j_object = j_env[0].CallStaticObjectMethodA(
                        j_env, j_class, self.j_method, j_args)
            check_exception(j_env)
            if j_object != NULL:
                ret = convert_jobject_to_python(
                        j_env, self.definition_return, j_object)
                j_env[0].DeleteLocalRef(j_env, j_object)
        elif r == '[':
            r = self.definition_return[1:]
            with nogil:
                j_object = j_env[0].CallStaticObjectMethodA(
                        j_env, j_class, self.j_method, j_args)
            check_exception(j_env)
            if j_object != NULL:
                ret = convert_jarray_to_python(j_env, r, j_object)
                j_env[0].DeleteLocalRef(j_env, j_object)
        else:
            raise Exception('Invalid return definition?')

        check_exception(j_env)
        return ret


cdef class JavaMultipleMethod(JavaMember):
    cdef list definitions
    cdef list methods

    def __repr__(self):
        return (f"<JavaMultipleMethod {self.methods}>")

    def __init__(self, definitions, **kwargs):
        super(JavaMultipleMethod, self).__init__()
        self.definitions = definitions
        self.methods = []

    def __get__(self, obj, objtype):
        return lambda *args: self(obj, *args)

    def set_resolve_info(self, jc, bytes name):
        super(JavaMultipleMethod, self).set_resolve_info(jc, name)
        for signature, static, varargs in self.definitions:
            jm = JavaMethod(signature, static=static, varargs=varargs)
            jm.set_resolve_info(jc, name)
            self.methods.append(jm)

    def __call__(self, obj, *args):
        cdef JavaMethod jm
        cdef list scores = []

        for jm in self.methods:
            sign_args = jm.definition_args
            if jm.is_varargs:
                args_ = args[:len(sign_args) - 1] + (args[len(sign_args) - 1:],)
            else:
                args_ = args

            score = calculate_score(sign_args, args_, jm.is_varargs)
            if score > 0:
                scores.append((score, jm))
        if not scores:
            raise AttributeError(f"No methods matching arguments {args}: options are {self.methods}")

        # FIXME this cannot be how Java does it: if multiple methods have the same score, we'll
        # call one at random.
        scores.sort()
        score, jm = scores[-1]
        return jm.__get__(obj, type(obj))(*args)


# FIXME remove these when regenerating bootstrap class proxies: they add nothing.
class JavaStaticMethod(JavaMethod):
    def __init__(self, definition, **kwargs):
        kwargs['static'] = True
        super(JavaStaticMethod, self).__init__(definition, **kwargs)

class JavaStaticField(JavaField):
    def __init__(self, definition, **kwargs):
        kwargs['static'] = True
        super(JavaStaticField, self).__init__(definition, **kwargs)
