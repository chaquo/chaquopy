from collections import defaultdict
import itertools
import keyword


# The public name is `jclass`, but that would conflict with the JNI typedef of the same name.
# __init__.py performs the renaming.
def jklass(clsname):
    """Returns a proxy class for the given fully-qualified Java class name. The name may use either
    `.` or `/` notation. To refer to a nested or inner class, separate it from the containing
    class with `$`, e.g. `java.lang.Map$Entry`. If the name cannot be resolved, a
    :any:`JavaException` is raised.
    """  # Further documentation in python.rst
    clsname = clsname.replace('/', '.')
    if clsname.startswith("["):
        raise ValueError("Cannot reflect an array type")
    if clsname in java.primitives_by_name:
        raise ValueError("Cannot reflect a primitive type")
    if clsname.startswith("L") and clsname.endswith(";"):
        clsname = clsname[1:-1]
    if clsname.startswith('$Proxy'):
        # The Dalvik VM is not able to give us introspection on these (FindClass returns NULL).
        return jklass("java.lang.Object")

    cls = jclass_cache.get(clsname)
    if not cls:
        cls = JavaClass(clsname, (JavaObject,), {})
        reflect_class(cls)
    return cls


jclass_cache = {}


# This isn't done during module initialization because we don't have a JVM yet, and we don't
# want to automatically start one because we might already be in a Java process.
def setup_bootstrap_classes():
    # Declare only the methods used in this file.
    global Class, Modifier, Method, Field, Constructor
    if "Class" in globals():
        raise Exception("setup_bootstrap_classes called more than once")

    Class = JavaClass("java.lang.Class", (JavaObject,), {})
    add_member(Class, "getClasses", JavaMethod('()[Ljava/lang/Class;'))
    add_member(Class, "getConstructors", JavaMethod('()[Ljava/lang/reflect/Constructor;'))
    add_member(Class, "getFields", JavaMethod('()[Ljava/lang/reflect/Field;'))
    add_member(Class, "getMethods", JavaMethod('()[Ljava/lang/reflect/Method;'))
    add_member(Class, "getName", JavaMethod('()Ljava/lang/String;'))

    Modifier = JavaClass("java.lang.reflect.Modifier", (JavaObject,), {})
    add_member(Modifier, "isAbstract", JavaMethod('(I)Z', static=True))
    add_member(Modifier, "isFinal", JavaMethod('(I)Z', static=True))
    add_member(Modifier, "isStatic", JavaMethod('(I)Z', static=True))

    Method = JavaClass("java.lang.reflect.Method", (JavaObject,), {})
    add_member(Method, "getDeclaringClass", JavaMethod('()Ljava/lang/Class;'))
    add_member(Method, "getModifiers", JavaMethod('()I'))
    add_member(Method, "getName", JavaMethod('()Ljava/lang/String;'))
    add_member(Method, "getParameterTypes", JavaMethod('()[Ljava/lang/Class;'))
    add_member(Method, "getReturnType", JavaMethod('()Ljava/lang/Class;'))
    add_member(Method, "isSynthetic", JavaMethod('()Z'))
    add_member(Method, "isVarArgs", JavaMethod('()Z'))

    Field = JavaClass("java.lang.reflect.Field", (JavaObject,), {})
    add_member(Field, "getDeclaringClass", JavaMethod('()Ljava/lang/Class;'))
    add_member(Field, "getModifiers", JavaMethod('()I'))
    add_member(Field, "getName", JavaMethod('()Ljava/lang/String;'))
    add_member(Field, "getType", JavaMethod('()Ljava/lang/Class;'))

    Constructor = JavaClass("java.lang.reflect.Constructor", (JavaObject,), {})
    add_member(Constructor, "getDeclaringClass", JavaMethod('()Ljava/lang/Class;'))
    add_member(Constructor, "getModifiers", JavaMethod('()I'))
    add_member(Constructor, "getName", JavaMethod('()Ljava/lang/String;'))
    add_member(Constructor, "getParameterTypes", JavaMethod('()[Ljava/lang/Class;'))
    add_member(Constructor, "isSynthetic", JavaMethod('()Z'))
    add_member(Constructor, "isVarArgs", JavaMethod('()Z'))

    for cls in [Class, Modifier, Method, Field, Constructor]:
        reflect_class(cls)


class JavaClass(type):
    def __new__(metacls, classname, bases, classDict):
        classDict["_chaquopy_j_klass"] = CQPEnv().FindClass(classname).global_ref()

        # TODO #5153 disabled until tested, and should also generate a setter.
        # if name != 'getClass' and bean_getter(name) and len(method.getParameterTypes()) == 0:
        #     classDict[lower_name(name[3:])] = \
        #         (lambda n: property(lambda self: getattr(self, n)()))(name)
        #
        # TODO #5154 disabled until tested, and should also implement other container
        # interfaces.
        # for iclass in c.getInterfaces():
        #     if iclass.getName() == 'java.util.List':
        #         classDict['__getitem__'] = lambda self, index: self.get(index)
        #         classDict['__len__'] = lambda self: self.size()

        # classname must be "str" type, whatever that is on this Python version.
        cls = type.__new__(metacls, str(classname), bases, classDict)
        jclass_cache[classname] = cls
        return cls

    # Override to prevent modification of class dict.
    def __setattr__(cls, key, value):
        set_attribute(cls, None, key, value)


def lower_name(s):
    return s[:1].lower() + s[1:] if s else ''

def bean_getter(s):
    return (s.startswith('get') and len(s) > 3 and s[3].isupper()) or (s.startswith('is') and len(s) > 2 and s[2].isupper())


# TODO #5168 Replicate Java class hierarchy
#
# To avoid conflict with Java member names, all internal-use members of this class or its
# subclasses should have the prefix "_chaquopy_".
class JavaObject(object):
    def __init__(self, *args, JNIRef instance=None):
        super().__init__()
        cdef JNIEnv *env = get_jnienv()
        if instance is not None:
            if not env[0].IsInstanceOf(env, instance.obj, (<JNIRef?>self._chaquopy_j_klass).obj):
                raise TypeError(f"cannot create {type(self).__name__} proxy from "
                                f"{lookup_java_object_name(env, instance.obj)} instance")
            this = instance.global_ref()
        else:
            # Java SE 8 raises an InstantiationException when calling NewObject on an abstract
            # class, but Android 6 crashes with a CheckJNI error.
            klass = Class(instance=self._chaquopy_j_klass)
            if Modifier.isAbstract(klass.getModifiers()):
                raise TypeError(f"{type(self).__name__} is abstract and cannot be instantiated")
            try:
                constructor = getattr(type(self), "<init>")
            except AttributeError:
                raise TypeError(f"{type(self).__name__} has no accessible constructors")
            this = constructor(*args)
        object.__setattr__(self, "_chaquopy_this", this)

    # Override to prevent modification of instance dict.
    def __setattr__(self, key, value):
        set_attribute(type(self), self, key, value)

    def __repr__(self):
        if self._chaquopy_this:
            ts = str(self)
            if ts is not None and \
               ts.startswith(type(self).__name__):  # e.g. "java.lang.Object@28d93b30"
                return f"<{ts}>"
            else:
                return f"<{type(self).__name__} '{ts}'>"
        else:
            return f"<{type(self).__name__} (no instance)>"

    def __str__(self):
        return self.toString()

    def __hash__(self):
        return self.hashCode()

    def __eq__(self, other):
        return self.equals(other)

    def __ne__(self, other):  # Not automatic in Python 2
        return not (self == other)


def set_attribute(cls, obj, key, value):
    try:
        member = cls.__dict__[key]
    except KeyError:
        subject = f"'{cls.__name__}' object" if obj else f"type object '{cls.__name__}'"
        raise AttributeError(f"{subject} has no attribute '{key}'")
    if not isinstance(member, JavaField):
        raise AttributeError(f"'{cls.__name__}.{key}' is not a field")
    member.__set__(obj, value)


def reflect_class(cls):
    klass = Class(instance=cls._chaquopy_j_klass)

    name_key = lambda m: m.getName()
    all_methods = klass.getMethods() + klass.getConstructors()
    all_methods.sort(key=name_key)
    for name, methods in itertools.groupby(all_methods, name_key):
        member = None
        for method in methods:
            if isinstance(method, Constructor):
                name = "<init>"
            if method.isSynthetic(): continue  # TODO #5232 test this
            jm = JavaMethod(method)
            if member is None:
                member = jm
            elif isinstance(member, JavaMethod):
                member = JavaMultipleMethod([member, jm])
            else:
                (<JavaMultipleMethod?>member).methods.append(jm)
        add_member(cls, name, member)

    for field in klass.getFields():
        # TODO #5183 method hides field with same name.
        # TODO #5208 depending on the order of getFields(), we may hide the wrong field in
        # case of a superclass and subclass having fields with the same name.
        add_member(cls, field.getName(), JavaField(field))

    for nested_klass in klass.getClasses():
        # TODO #5208 may have a similar hiding problem to fields
        name = nested_klass.getSimpleName()  # Returns empty string for anonymous classes.
        if name:
            add_member(cls, name, jklass(nested_klass.getName()))  # TODO add a JavaMember subclass which delays the jklass call

    aliases = {}
    for name, member in six.iteritems(cls.__dict__):
        # As recommended by PEP 8, members whose names are reserved words can be accessed by
        # appending an underscore. The original name is still accessible via getattr().
        if is_reserved_word(name):
            aliases[name + "_"] =  member
    for alias, member in six.iteritems(aliases):
        if alias not in cls.__dict__:
            type.__setattr__(cls, alias, member)


def add_member(cls, name, member):
    if name not in cls.__dict__:  # TODO #5183 method hides field with same name.
        type.__setattr__(cls, name, member)  # Direct modification of cls.__dict__ is not allowed.
        if isinstance(member, JavaMember):
            member.added_to_class(cls, name)


# Ensure the same aliases are available on all Python versions
EXTRA_RESERVED_WORDS = {'exec', 'print',                      # Removed in Python 3.0
                        'nonlocal', 'True', 'False', 'None',  # Added in Python 3.0
                        'async', 'await'}                     # Added in Python 3.5

def is_reserved_word(word):
    return keyword.iskeyword(word) or word in EXTRA_RESERVED_WORDS


cdef class JavaMember(object):
    cdef cls
    cdef basestring name

    def added_to_class(self, cls, name):
        self.cls = cls
        self.name = name

    def fqn(self):
        return f"{self.cls.__name__}.{self.name}"


cdef class JavaSimpleMember(JavaMember):
    cdef reflected
    cdef JNIRef j_klass
    cdef basestring definition
    cdef bint is_static

    def __init__(self, definition_or_reflected, *, static):
        if isinstance(definition_or_reflected, str):
            self.definition = definition_or_reflected
        else:
            self.reflected = definition_or_reflected
        self.is_static = static

    def resolve(self):
        if self.reflected:
            self.j_klass = self.reflected.getDeclaringClass()._chaquopy_this
            self.is_static = Modifier.isStatic(self.reflected.getModifiers())
        else:
            self.j_klass = self.cls._chaquopy_j_klass


cdef class JavaField(JavaSimpleMember):
    cdef jfieldID j_field
    cdef bint is_final

    def __repr__(self):
        self.resolve()
        return (f"<JavaField "
                f"{'static ' if self.is_static else ''}"
                f"{'final ' if self.is_final else ''}"
                f"{java.sig_to_java(self.definition)} {self.fqn()}>")

    def __init__(self, definition_or_reflected, *, static=False, final=False):
        super().__init__(definition_or_reflected, static=static)
        self.is_final = final

    def resolve(self):
        if self.j_field: return

        super().resolve()
        if self.reflected:
            self.definition = java.jni_sig(self.reflected.getType())
            self.is_final = Modifier.isFinal(self.reflected.getModifiers())

        env = CQPEnv()
        if self.is_static:
            self.j_field = env.GetStaticFieldID(self.j_klass, self.name, self.definition)
        else:
            self.j_field = env.GetFieldID(self.j_klass, self.name, self.definition)

    def __get__(self, obj, objtype):
        self.resolve()
        if self.is_static:
            return self.read_static_field()
        else:
            if obj is None:
                raise AttributeError(f'Cannot access {self.fqn()} in static context')
            return self.read_field(obj)

    def __set__(self, obj, value):
        self.resolve()
        if self.is_final:  # 'final' is not enforced by JNI, so we need to do it ourselves.
            raise AttributeError(f"{self.fqn()} is a final field")

        if self.is_static:
            self.write_static_field(value)
        else:
            # obj would never be None with the standard descriptor protocol, but we extend the
            # protocol by overriding JavaClass.__setattr__.
            if obj is None:
                raise AttributeError(f'Cannot access {self.fqn()} in static context')
            self.write_field(obj, value)

    # Cython auto-generates range checking code for the integral types.
    cdef write_field(self, obj, value):
        cdef JNIEnv *j_env = get_jnienv()
        cdef jobject j_self = (<JNIRef?>obj._chaquopy_this).obj
        j_value = p2j(j_env, self.definition, value)

        r = self.definition[0]
        if r == 'Z':
            j_env[0].SetBooleanField(j_env, j_self, self.j_field, j_value)
        elif r == 'B':
            j_env[0].SetByteField(j_env, j_self, self.j_field, j_value)
        elif r == 'C':
            check_range_char(j_value)
            j_env[0].SetCharField(j_env, j_self, self.j_field, ord(j_value))
        elif r == 'S':
            j_env[0].SetShortField(j_env, j_self, self.j_field, j_value)
        elif r == 'I':
            j_env[0].SetIntField(j_env, j_self, self.j_field, j_value)
        elif r == 'J':
            j_env[0].SetLongField(j_env, j_self, self.j_field, j_value)
        elif r == 'F':
            check_range_float32(j_value)
            j_env[0].SetFloatField(j_env, j_self, self.j_field, j_value)
        elif r == 'D':
            j_env[0].SetDoubleField(j_env, j_self, self.j_field, j_value)
        elif r in 'L[':
            # SetObjectField cannot throw an exception, so p2j must never return an
            # incompatible object.
            j_env[0].SetObjectField(j_env, j_self, self.j_field, (<JNIRef?>j_value).obj)
        else:
            raise Exception(f"Invalid definition for {self.fqn()}: '{self.definition}'")

    cdef read_field(self, obj):
        cdef JNIEnv *j_env = get_jnienv()
        cdef jobject j_self = (<JNIRef?>obj._chaquopy_this).obj
        r = self.definition[0]
        if r == 'Z':
            return bool(j_env[0].GetBooleanField(j_env, j_self, self.j_field))
        elif r == 'B':
            return j_env[0].GetByteField(j_env, j_self, self.j_field)
        elif r == 'C':
            return six.unichr(j_env[0].GetCharField(j_env, j_self, self.j_field))
        elif r == 'S':
            return j_env[0].GetShortField(j_env, j_self, self.j_field)
        elif r == 'I':
            return j_env[0].GetIntField(j_env, j_self, self.j_field)
        elif r == 'J':
            return j_env[0].GetLongField(j_env, j_self, self.j_field)
        elif r == 'F':
            return j_env[0].GetFloatField(j_env, j_self, self.j_field)
        elif r == 'D':
            return j_env[0].GetDoubleField(j_env, j_self, self.j_field)
        elif r in 'L[':
            j_object = LocalRef.adopt(j_env, j_env[0].GetObjectField(j_env, j_self, self.j_field))
            return j2p(j_env, j_object)
        else:
            raise Exception(f"Invalid definition for {self.fqn()}: '{self.definition}'")

    # Cython auto-generates range checking code for the integral types.
    cdef write_static_field(self, value):
        cdef jclass j_class = self.j_klass.obj
        cdef JNIEnv *j_env = get_jnienv()
        j_value = p2j(j_env, self.definition, value)

        r = self.definition[0]
        if r == 'Z':
            j_env[0].SetStaticBooleanField(j_env, j_class, self.j_field, j_value)
        elif r == 'B':
            j_env[0].SetStaticByteField(j_env, j_class, self.j_field, j_value)
        elif r == 'C':
            check_range_char(j_value)
            j_env[0].SetStaticCharField(j_env, j_class, self.j_field, ord(j_value))
        elif r == 'S':
            j_env[0].SetStaticShortField(j_env, j_class, self.j_field, j_value)
        elif r == 'I':
            j_env[0].SetStaticIntField(j_env, j_class, self.j_field, j_value)
        elif r == 'J':
            j_env[0].SetStaticLongField(j_env, j_class, self.j_field, j_value)
        elif r == 'F':
            check_range_float32(j_value)
            j_env[0].SetStaticFloatField(j_env, j_class, self.j_field, j_value)
        elif r == 'D':
            j_env[0].SetStaticDoubleField(j_env, j_class, self.j_field, j_value)
        elif r in 'L[':
            # SetStaticObjectField cannot throw an exception, so p2j must never return an
            # incompatible object.
            j_env[0].SetStaticObjectField(j_env, j_class, self.j_field, (<JNIRef?>j_value).obj)
        else:
            raise Exception(f"Invalid definition for {self.fqn()}: '{self.definition}'")

    cdef read_static_field(self):
        cdef jclass j_class = self.j_klass.obj
        cdef JNIEnv *j_env = get_jnienv()
        r = self.definition[0]
        if r == 'Z':
            return bool(j_env[0].GetStaticBooleanField(j_env, j_class, self.j_field))
        elif r == 'B':
            return j_env[0].GetStaticByteField(j_env, j_class, self.j_field)
        elif r == 'C':
            return six.unichr(j_env[0].GetStaticCharField(j_env, j_class, self.j_field))
        elif r == 'S':
            return j_env[0].GetStaticShortField(j_env, j_class, self.j_field)
        elif r == 'I':
            return j_env[0].GetStaticIntField(j_env, j_class, self.j_field)
        elif r == 'J':
            return j_env[0].GetStaticLongField(j_env, j_class, self.j_field)
        elif r == 'F':
            return j_env[0].GetStaticFloatField(j_env, j_class, self.j_field)
        elif r == 'D':
            return j_env[0].GetStaticDoubleField(j_env, j_class, self.j_field)
        elif r in 'L[':
            j_object = LocalRef.adopt(j_env, j_env[0].GetStaticObjectField(j_env, j_class,
                                                                           self.j_field))
            return j2p(j_env, j_object)
        else:
            raise Exception(f"Invalid definition for {self.fqn()}: '{self.definition}'")


cdef class JavaMethod(JavaSimpleMember):
    cdef jmethodID j_method
    cdef basestring definition_return
    cdef tuple definition_args
    cdef bint is_constructor
    cdef bint is_varargs

    def __repr__(self):
        self.resolve()
        return (f"<JavaMethod("
                f"{'static ' if self.is_static else ''}"
                f"{java.sig_to_java(self.definition_return)} {self.fqn()}{self.format_args()})>")

    def format_args(self):
        return java.args_sig_to_java(self.definition_args, self.is_varargs)

    def __init__(self, definition_or_reflected, *, static=False, varargs=False):
        super().__init__(definition_or_reflected, static=static)
        self.is_varargs = varargs

    def resolve(self):
        if self.j_method: return

        super().resolve()
        if self.reflected:
            return_type = (java.jvoid if isinstance(self.reflected, Constructor)
                           else self.reflected.getReturnType())
            self.definition = java.jni_method_sig(return_type, self.reflected.getParameterTypes())
            self.is_varargs = self.reflected.isVarArgs()

        env = CQPEnv()
        if self.is_static:
            self.j_method = env.GetStaticMethodID(self.j_klass, self.name, self.definition)
        else:
            self.j_method = env.GetMethodID(self.j_klass, self.name, self.definition)
        self.definition_return, self.definition_args = java.split_method_sig(self.definition)
        self.is_constructor = (self.name == "<init>")

    def __get__(self, obj, objtype):
        self.resolve()
        if obj is None or self.is_static or self.is_constructor:
            return self
        else:
            return lambda *args: self(obj, *args)

    def __call__(self, *args):
        cdef jvalue *j_args = NULL
        cdef tuple d_args = self.definition_args
        cdef JNIEnv *j_env = get_jnienv()

        if self.is_static or self.is_constructor:
            obj = None
        else:
            obj, args = self.get_this(j_env, args)

        # Exception types and wording are based on Python 2.7.
        if self.is_varargs:
            if len(args) < len(d_args) - 1:
                raise TypeError(f'{self.fqn()} takes at least {plural(len(d_args) - 1, "argument")} '
                                f'({len(args)} given)')

            if len(args) == len(d_args) and assignable_to_array(d_args[-1], args[-1]):
                # As in Java, passing a single None as the varargs parameter will be
                # interpreted as a null array. To pass an an array of one null, use [None].
                pass  # Non-varargs call.
            else:
                args = args[:len(d_args) - 1] + (args[len(d_args) - 1:],)
        if len(args) != len(d_args):
            raise TypeError(f'{self.fqn()} takes {plural(len(d_args), "argument")} '
                            f'({len(args)} given)')

        p2j_args = [p2j(j_env, argtype, arg)
                    for argtype, arg in six.moves.zip(d_args, args)]
        if len(args):
            j_args = <jvalue*>alloca(sizeof(jvalue) * len(d_args))
            populate_args(j_env, d_args, j_args, p2j_args)

        if self.is_constructor:
            result = self.call_constructor(j_env, j_args)
        elif self.is_static:
            result = self.call_static_method(j_env, j_args)
        else:
            result = self.call_method(j_env, obj, j_args)

        copy_output_args(d_args, args, p2j_args)
        return result

    # Exception types and wording are based on Python 2.7.
    cdef get_this(self, JNIEnv *j_env, args):
        if not args:
            got = "nothing"
        else:
            obj = args[0]
            if isinstance(obj, JavaObject) and \
               j_env[0].IsInstanceOf(j_env, (<JNIRef?>obj._chaquopy_this).obj, self.j_klass.obj):
                return obj, args[1:]
            else:
                got = f"{type(obj).__name__} instance"
        raise TypeError(f"Unbound method {self.fqn()} must be called with {self.cls.__name__} "
                        f"instance as first argument (got {got} instead)")

    cdef GlobalRef call_constructor(self, JNIEnv *j_env, jvalue *j_args):
        cdef jobject j_self
        with nogil:
            j_self = j_env[0].NewObjectA(j_env, self.j_klass.obj, self.j_method, j_args)
        check_exception(j_env)
        return LocalRef.adopt(j_env, j_self).global_ref()

    cdef call_method(self, JNIEnv *j_env, obj, jvalue *j_args):
        # These temporary variables are required because Python objects can't be touched during
        # "with nogil".
        cdef jboolean j_boolean
        cdef jbyte j_byte
        cdef jchar j_char
        cdef jshort j_short
        cdef jint j_int
        cdef jlong j_long
        cdef jfloat j_float
        cdef jdouble j_double
        cdef jobject j_object

        cdef jobject j_self = (<JNIRef?>obj._chaquopy_this).obj
        ret = None
        r = self.definition_return[0]
        if r == 'V':
            with nogil:
                j_env[0].CallVoidMethodA(j_env, j_self, self.j_method, j_args)
        elif r == 'Z':
            with nogil:
                j_boolean = j_env[0].CallBooleanMethodA(j_env, j_self, self.j_method, j_args)
            ret = bool(j_boolean)
        elif r == 'B':
            with nogil:
                j_byte = j_env[0].CallByteMethodA(j_env, j_self, self.j_method, j_args)
            ret = j_byte
        elif r == 'C':
            with nogil:
                j_char = j_env[0].CallCharMethodA(j_env, j_self, self.j_method, j_args)
            ret = six.unichr(j_char)
        elif r == 'S':
            with nogil:
                j_short = j_env[0].CallShortMethodA(j_env, j_self, self.j_method, j_args)
            ret = j_short
        elif r == 'I':
            with nogil:
                j_int = j_env[0].CallIntMethodA(j_env, j_self, self.j_method, j_args)
            ret = j_int
        elif r == 'J':
            with nogil:
                j_long = j_env[0].CallLongMethodA(j_env, j_self, self.j_method, j_args)
            ret = j_long
        elif r == 'F':
            with nogil:
                j_float = j_env[0].CallFloatMethodA(j_env, j_self, self.j_method, j_args)
            ret = j_float
        elif r == 'D':
            with nogil:
                j_double = j_env[0].CallDoubleMethodA(j_env, j_self, self.j_method, j_args)
            ret = j_double
        elif r in 'L[':
            with nogil:
                j_object = j_env[0].CallObjectMethodA(j_env, j_self, self.j_method, j_args)
            check_exception(j_env)
            ret = j2p(j_env, LocalRef.adopt(j_env, j_object))
        else:
            raise Exception(f"Invalid definition for {self.fqn()}: '{self.definition_return}'")

        check_exception(j_env)
        return ret

    cdef call_static_method(self, JNIEnv *j_env, jvalue *j_args):
        # These temporary variables are required because Python objects can't be touched during
        # "with nogil".
        cdef jboolean j_boolean
        cdef jbyte j_byte
        cdef jchar j_char
        cdef jshort j_short
        cdef jint j_int
        cdef jlong j_long
        cdef jfloat j_float
        cdef jdouble j_double
        cdef jobject j_object

        ret = None
        cdef jclass j_class = self.j_klass.obj
        r = self.definition_return[0]
        if r == 'V':
            with nogil:
                j_env[0].CallStaticVoidMethodA(j_env, j_class, self.j_method, j_args)
        elif r == 'Z':
            with nogil:
                j_boolean = j_env[0].CallStaticBooleanMethodA(j_env, j_class, self.j_method, j_args)
            ret = bool(j_boolean)
        elif r == 'B':
            with nogil:
                j_byte = j_env[0].CallStaticByteMethodA(j_env, j_class, self.j_method, j_args)
            ret = j_byte
        elif r == 'C':
            with nogil:
                j_char = j_env[0].CallStaticCharMethodA(j_env, j_class, self.j_method, j_args)
            ret = six.unichr(j_char)
        elif r == 'S':
            with nogil:
                j_short = j_env[0].CallStaticShortMethodA(j_env, j_class, self.j_method, j_args)
            ret = j_short
        elif r == 'I':
            with nogil:
                j_int = j_env[0].CallStaticIntMethodA(j_env, j_class, self.j_method, j_args)
            ret = j_int
        elif r == 'J':
            with nogil:
                j_long = j_env[0].CallStaticLongMethodA(j_env, j_class, self.j_method, j_args)
            ret = j_long
        elif r == 'F':
            with nogil:
                j_float = j_env[0].CallStaticFloatMethodA(j_env, j_class, self.j_method, j_args)
            ret = j_float
        elif r == 'D':
            with nogil:
                j_double = j_env[0].CallStaticDoubleMethodA(j_env, j_class, self.j_method, j_args)
            ret = j_double
        elif r in 'L[':
            with nogil:
                j_object = j_env[0].CallStaticObjectMethodA(j_env, j_class, self.j_method, j_args)
            check_exception(j_env)
            ret = j2p(j_env, LocalRef.adopt(j_env, j_object))
        else:
            raise Exception(f"Invalid definition for {self.fqn()}: '{self.definition_return}'")

        check_exception(j_env)
        return ret


cdef class JavaMultipleMethod(JavaMember):
    cdef list methods
    cdef dict overload_cache

    def __repr__(self):
        return f"JavaMultipleMethod({self.methods})"

    def __init__(self, methods):
        self.methods = methods
        self.overload_cache = {}

    def added_to_class(self, cls, name):
        super().added_to_class(cls, name)
        for jm in self.methods:
            (<JavaMethod?>jm).added_to_class(cls, name)

    def __get__(self, obj, objtype):
        return lambda *args: self(obj, *args)

    def __call__(self, obj, *args):
        args_types = tuple(map(type, args))
        best_overload = self.overload_cache.get(args_types)
        if not best_overload:
            for jm in self.methods:
                (<JavaMethod?>jm).resolve()

            # JLS 15.12.2.2. "Identify Matching Arity Methods Applicable by Subtyping"
            varargs = False
            applicable = self.find_applicable(obj, args, autobox=False, varargs=False)

            # JLS 15.12.2.3. "Identify Matching Arity Methods Applicable by Method Invocation
            # Conversion"
            if not applicable:
                applicable = self.find_applicable(obj, args, autobox=True, varargs=False)

            # JLS 15.12.2.4. "Identify Applicable Variable Arity Methods"
            if not applicable:
                varargs = True
                applicable = self.find_applicable(obj, args, autobox=True, varargs=True)

            if not applicable:
                raise TypeError(self.overload_err(f"cannot be applied to", args, self.methods))

            # JLS 15.12.2.5. "Choosing the Most Specific Method"
            maximal = []
            for jm1 in applicable:
                if not any([better_overload(jm2, jm1, args_types, varargs=varargs)
                            for jm2 in applicable if jm2 is not jm1]):
                    maximal.append(jm1)
            if len(maximal) != 1:
                raise TypeError(self.overload_err(f"is ambiguous for arguments", args,
                                                  maximal if maximal else applicable))
            best_overload = maximal[0]
            self.overload_cache[args_types] = best_overload

        return best_overload.__get__(obj, type(obj))(*args)

    def find_applicable(self, obj, args, *, autobox, varargs):
        result = []
        cdef JavaMethod jm
        for jm in self.methods:
            if obj is None and not (jm.is_static or jm.is_constructor):  # Unbound method
                if not args: continue
                args_except_this = args[1:]
            else:
                args_except_this = args
            if not (varargs and not jm.is_varargs) and \
               is_applicable(jm.definition_args, args_except_this, autobox, varargs):
                result.append(jm)
        return result

    def overload_err(self, msg, args, methods):
        args_type_names = "({})".format(", ".join([type(a).__name__ for a in args]))
        return (f"{self.fqn()} {msg} {args_type_names}: options are " +
                ", ".join([jm.format_args() for jm in methods]))
