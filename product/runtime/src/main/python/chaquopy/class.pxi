import keyword
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


# FIXME override setattr on both class and object so that assignment to methods or nonexistent
# fields doesn't work (see static field __set__ note below).
#
# cdef'ed metaclasses don't work with six's with_metaclass (https://trac.sagemath.org/ticket/18503)
class JavaClass(type):
    def __new__(metacls, classname, bases, classDict):
        # These are defined here rather than in JavaObject because cdef classes are required to
        # use __richcmp__ instead.
        classDict["__eq__"] = lambda self, other: self.equals(other)
        classDict["__ne__"] = lambda self, other: not self.equals(other)

        # TODO disabled until tested (#5154), and should also implement other container
        # interfaces.
        #
        # for iclass in c.getInterfaces():
        #     if iclass.getName() == 'java.util.List':
        #         classDict['__getitem__'] = lambda self, index: self.get(index)
        #         classDict['__len__'] = lambda self: self.size()

        return type.__new__(metacls, classname, bases, classDict)

    def __init__(cls, classname, bases, classDict):
        cdef JNIEnv *j_env = get_jnienv()
        cls.__javaclass__ = cls.__javaclass__.replace("/", ".")
        jni_clsname = cls.__javaclass__.replace(".", "/")
        j_cls = LocalRef.adopt(j_env, j_env[0].FindClass(j_env, str_for_c(jni_clsname)))
        if not j_cls:
            expect_exception(j_env, f"FindClass failed for {cls.__javaclass__}")
        cls.j_cls = j_cls.global_ref()

        reserved_word_aliases = {}
        for name, value in six.iteritems(classDict):
            if isinstance(value, JavaMember):
                value.set_resolve_info(cls, str_for_c(name))
                if is_reserved_word(name):
                    # As recommended by PEP 8, append an underscore to member names which are
                    # reserved words. (The original name is still accessible via getattr().)
                    reserved_word_aliases[name + "_"] = value
        for name, value in six.iteritems(reserved_word_aliases):
            if not hasattr(cls, name):
                setattr(cls, name, value)


# Ensure the same aliases are available on all Python versions
EXTRA_RESERVED_WORDS = {'exec', 'print',                      # Removed in Python 3.0
                        'nonlocal', 'True', 'False', 'None',  # Python 3.0
                        'async', 'await'}                     # Python 3.7

def is_reserved_word(word):
    return keyword.iskeyword(word) or word in EXTRA_RESERVED_WORDS


# TODO it would simplify things if JavaClass was the java.lang.Class proxy, and JavaObject was
# the java.lang.Object proxy. Maybe we could even integrate this into the Python metaclass
# system, so that type(String("foo")) is String, type(String) is Class, and type(Class) is type.
#
# TODO #5168 Replicate Java class hierarchy
cdef class JavaObject(object):
    '''Base class for Python -> Java proxy classes'''

    # Member variables declared in .pxd

    def __init__(self, *args, JNIRef instance=None):
        super(JavaObject, self).__init__()
        cdef JNIEnv *env = get_jnienv()
        if instance is not None:
            if not env[0].IsInstanceOf(env, instance.obj, (<JNIRef?>self.j_cls).obj):
                raise TypeError(f"Cannot create {self.__javaclass__} proxy from a "
                                f"{lookup_java_object_name(env, instance.obj)} instance")
            self.j_self = instance.global_ref()
        else:
            try:
                constructor = self.__javaconstructor__
            except AttributeError:
                raise TypeError(f"{self.__javaclass__} has no accessible constructors")
            self.j_self = constructor(*args)

    def __repr__(self):
        if self.j_self:
            ts = str(self)
            if ts is not None and \
               self.__javaclass__.split(".")[-1] in ts:  # e.g. "java.lang.Object@28d93b30"
                return f"<'{ts}'>"
            else:
                return f"<{self.__javaclass__} '{ts}'>"
        else:
            return f"<{self.__javaclass__} (no instance)>"

    def __str__(self):
        return self.toString()

    def __hash__(self):
        return self.hashCode()


cdef class JavaMember(object):
    cdef jc
    cdef name
    cdef bint is_static

    def __init__(self, bint static=False):
        self.is_static = static

    def classname(self):
        return self.jc.__javaclass__ if self.jc else None

    def set_resolve_info(self, jc, name):
        # jc is the JavaClass of which we are a member, so this will cause a reference cycle.
        self.jc = jc
        self.name = name


cdef class JavaField(JavaMember):
    cdef jfieldID j_field
    cdef definition

    def __repr__(self):
        # TODO #5155 don't expose JNI signatures to users
        return (f"JavaField({self.definition!r}, class={self.classname()!r}, name={self.name!r}"
                f"{', static=True' if self.is_static else ''})")

    def __init__(self, definition, *, static=False):
        super(JavaField, self).__init__(static)
        self.definition = str_for_c(definition)

    cdef jfieldID id(self) except NULL:
        self.ensure_field()
        return self.j_field

    cdef void ensure_field(self) except *:
        cdef JNIEnv *j_env = get_jnienv()
        if self.j_field != NULL:
            return
        if self.is_static:
            self.j_field = j_env[0].GetStaticFieldID(
                    j_env, (<GlobalRef?>self.jc.j_cls).obj, self.name, self.definition)
        else:
            self.j_field = j_env[0].GetFieldID(
                    j_env, (<GlobalRef?>self.jc.j_cls).obj, self.name, self.definition)
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
            j_self = (<JavaObject?>obj).j_self.obj
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
            j_self = (<JavaObject?>obj).j_self.obj
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
        cdef JNIRef j_object
        cdef JNIEnv *j_env = get_jnienv()

        r = self.definition[0]

        # FIXME perform range and type checks, unless Cython checks and errors are adequate.
        #
        # We don't implement auto-unboxing: see note in populate_args
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
            j_object = p2j(j_env, self.definition, value)
            j_env[0].SetObjectField(j_env, j_self, self.j_field, j_object.obj)
        # FIXME #5177 array fields
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
                ret = j2p(j_env, self.definition, j_object)
                j_env[0].DeleteLocalRef(j_env, j_object)
        elif r == '[':
            r = self.definition[1:]
            j_object = j_env[0].GetObjectField(
                    j_env, j_self, self.j_field)
            check_exception(j_env)
            if j_object != NULL:
                ret = j2p_array(j_env, r, j_object)
                j_env[0].DeleteLocalRef(j_env, j_object)
        else:
            raise Exception(f'Invalid field definition for {self}')

        check_exception(j_env)
        return ret

    cdef read_static_field(self):
        cdef jclass j_class = (<GlobalRef?>self.jc.j_cls).obj
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
                ret = j2p(j_env, self.definition, j_object)
                j_env[0].DeleteLocalRef(j_env, j_object)
        elif r == '[':
            r = self.definition[1:]
            j_object = j_env[0].GetStaticObjectField(
                    j_env, j_class, self.j_field)
            check_exception(j_env)
            if j_object != NULL:
                ret = j2p_array(j_env, r, j_object)
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
    cdef bint is_constructor
    cdef bint is_varargs

    def __repr__(self):
        # TODO #5155 don't expose JNI signatures to users
        return (f"JavaMethod({self.definition!r}, class={self.classname()!r}, name={self.name!r}"
                f"{', static=True' if self.is_static else ''}"
                f"{', varargs=True' if self.is_varargs else ''})")

    def __init__(self, definition, *, static=False, varargs=False):
        super(JavaMethod, self).__init__(static)
        self.definition = str_for_c(definition)
        self.definition_return, self.definition_args = parse_definition(definition)
        self.is_varargs = varargs

    def set_resolve_info(self, jc, name):
        if name == "__javaconstructor__":
            name = "<init>"
        self.is_constructor = (name == "<init>")
        super(JavaMethod, self).set_resolve_info(jc, name)

    cdef jmethodID id(self) except NULL:
        self.ensure_method()
        return self.j_method

    cdef void ensure_method(self) except *:
        if self.j_method != NULL:
            return
        cdef JNIEnv *j_env = get_jnienv()
        if self.name is None:
            raise JavaException('Unable to find a None method!')
        if self.is_static:
            self.j_method = j_env[0].GetStaticMethodID(
                    j_env, (<GlobalRef?>self.jc.j_cls).obj, self.name, self.definition)
        else:
            self.j_method = j_env[0].GetMethodID(
                    j_env, (<GlobalRef?>self.jc.j_cls).obj, self.name, self.definition)
        if self.j_method == NULL:
            expect_exception(j_env, f"Get[Static]Method failed for {self}")

    def __get__(self, obj, objtype):
        self.ensure_method()
        if obj is None and not (self.is_static or self.is_constructor):
            # We don't allow the user to get unbound method objects, because that wouldn't be
            # compatible with the way we implement overload resolution. (It might be possible
            # to fix this, but it's not worth the effort.)
            raise AttributeError(f'Cannot access {self} in static context')
        else:
            return lambda *args: self(obj, *args)

    def __call__(self, obj, *args):
        cdef jvalue *j_args = NULL
        cdef tuple d_args = self.definition_args
        cdef JNIEnv *j_env = get_jnienv()

        # Should never happen, but worth keeping as an extra defense against a native crash.
        if not self.is_static and not isinstance(obj, self.jc):
            raise TypeError(f"Unbound method {self} must be called with "
                            f"{self.jc.__name__} instance as first argument (got "
                            f"{type(obj).__name__} instance instead)")

        if self.is_varargs:
            if len(args) < len(d_args) - 1:
                raise TypeError(f'{self} takes at least {len(d_args) - 1} arguments '
                                f'({len(args)} given)')
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
                if self.is_constructor:
                    return self.call_constructor(j_env, j_args)
                if self.is_static:
                    return self.call_staticmethod(j_env, j_args)
                else:
                    return self.call_method(j_env, obj, j_args)
            finally:
                release_args(j_env, self.definition_args, j_args, args)

        finally:
            if j_args != NULL:
                free(j_args)

    cdef GlobalRef call_constructor(self, JNIEnv *j_env, jvalue *j_args):
        cdef jobject j_self = j_env[0].NewObjectA(j_env, (<GlobalRef?>self.jc.j_cls).obj,
                                                  self.j_method, j_args)
        check_exception(j_env)
        return LocalRef.adopt(j_env, j_self).global_ref()

    cdef call_method(self, JNIEnv *j_env, JavaObject obj, jvalue *j_args):
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
                ret = j2p(j_env, self.definition_return, j_object)
                j_env[0].DeleteLocalRef(j_env, j_object)
        elif r == '[':
            # FIXME can we combine this with the 'L' case?
            r = self.definition_return[1:]
            with nogil:
                j_object = j_env[0].CallObjectMethodA(
                        j_env, j_self, self.j_method, j_args)
            check_exception(j_env)
            if j_object != NULL:
                ret = j2p_array(j_env, r, j_object)
                j_env[0].DeleteLocalRef(j_env, j_object)
        else:
            raise Exception('Invalid return definition?')

        check_exception(j_env)
        return ret

    cdef call_staticmethod(self, JNIEnv *j_env, jvalue *j_args):
        cdef jclass j_class = (<GlobalRef?>self.jc.j_cls).obj
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
                ret = j2p(j_env, self.definition_return, j_object)
                j_env[0].DeleteLocalRef(j_env, j_object)
        elif r == '[':
            # FIXME can we combine this with the 'L' case?
            r = self.definition_return[1:]
            with nogil:
                j_object = j_env[0].CallStaticObjectMethodA(
                        j_env, j_class, self.j_method, j_args)
            check_exception(j_env)
            if j_object != NULL:
                ret = j2p_array(j_env, r, j_object)
                j_env[0].DeleteLocalRef(j_env, j_object)
        else:
            raise Exception('Invalid return definition?')

        check_exception(j_env)
        return ret


cdef class JavaMultipleMethod(JavaMember):
    cdef list methods
    cdef dict overload_cache

    def __repr__(self):
        return f"JavaMultipleMethod({self.methods})"

    def __init__(self, methods):
        super(JavaMultipleMethod, self).__init__()
        self.methods = methods
        self.overload_cache = {}

    def __get__(self, obj, objtype):
        return lambda *args: self(obj, *args)

    def set_resolve_info(self, jc, name):
        if name == "__javaconstructor__":
            name = "<init>"
        super(JavaMultipleMethod, self).set_resolve_info(jc, name)
        for jm in self.methods:
            (<JavaMethod?>jm).set_resolve_info(jc, name)

    def __call__(self, obj, *args):
        args_types = tuple(map(type, args))
        best_overload = self.overload_cache.get(args_types)
        if not best_overload:
            # JLS 15.12.2.2. Identify Matching Arity Methods
            applicable = [jm for jm in self.methods
                          if is_applicable((<JavaMethod?>jm).definition_args,
                                           args, varargs=False)]

            # JLS 15.12.2.4. Identify Applicable Variable Arity Methods
            if not applicable:
                applicable = [jm for jm in self.methods if (<JavaMethod?>jm).is_varargs and
                              is_applicable((<JavaMethod?>jm).definition_args,
                                           args, varargs=True)]
            if not applicable:
                raise TypeError(self.overload_err(f"cannot be applied to", args, self.methods))

            # JLS 15.12.2.5. Choosing the Most Specific Method
            maximal = []
            for jm1 in applicable:
                if not any([more_specific(jm2, jm1) for jm2 in applicable if jm2 is not jm1]):
                    maximal.append(jm1)
            if len(maximal) != 1:
                raise TypeError(self.overload_err(f"is ambiguous for arguments", args, maximal))
            best_overload = maximal[0]
            self.overload_cache[args_types] = best_overload

        return best_overload.__get__(obj, type(obj))(*args)

    def overload_err(self, msg, args, methods):
        # TODO #5155 don't expose JNI signatures to users
        args_type_names = "({})".format(", ".join([type(a).__name__ for a in args]))
        return (f"{self.classname()}.{self.name} {msg} {args_type_names}: options are " +
                ", ".join([f"{<JavaMethod?>jm).definition_args}" for jm in methods]))
