from collections import defaultdict
from itertools import chain, groupby
import keyword
from threading import RLock
from weakref import WeakValueDictionary


class_lock = RLock()
jclass_cache = {}
instance_cache = WeakValueDictionary()


# TODO #5167 this may fail in non-Java-created threads on Android, because they'll use the
# wrong ClassLoader.
def jclass(clsname):
    """Returns a proxy class for the given fully-qualified Java class name. The name may use either
    `.` or `/` notation. To refer to a nested or inner class, separate it from the containing
    class with `$`, e.g. `java.lang.Map$Entry`. If the name cannot be resolved, a
    `NoClassDefFoundError` is raised.
    """
    clsname = clsname.replace('/', '.')
    if clsname.startswith("["):
        raise ValueError("Cannot reflect an array type")  # But note that `jarray` shares jclass_cache
    if clsname in java.primitives_by_name:
        raise ValueError("Cannot reflect a primitive type")
    if clsname.startswith("L") and clsname.endswith(";"):
        clsname = clsname[1:-1]
    if clsname.startswith('$Proxy'):
        # The Dalvik VM is not able to give us introspection on these (FindClass returns NULL).
        return jclass("java.lang.Object")

    if not isinstance(clsname, str):
        clsname = str(clsname)

    with class_lock:
        cls = jclass_cache.get(clsname)
        if not cls:
            try:
                cls = jclass_proxy(clsname)
            except JavaException as e:
                # Java SE 8 throws NoClassDefFoundError like the JNI spec says, but Android 6
                # throws ClassNotFoundException. Hide this from our users.
                if isinstance(e, jclass("java.lang.ClassNotFoundException")):
                    ncdfe = jclass("java.lang.NoClassDefFoundError")(e.getMessage())
                    ncdfe.setStackTrace(e.getStackTrace())
                    raise ncdfe
                else:
                    raise
            reflect_class(cls)
        return cls


def jclass_proxy(cls_name, bases=None):
    return JavaClass(None, bases, dict(_chaquopy_name=cls_name))


class JavaClass(type):
    def __new__(metacls, name_ignored, bases, cls_dict):
        cls_name = cls_dict.pop("_chaquopy_name", None)
        if not cls_name:
            raise TypeError("Java classes can only be inherited using static_proxy or dynamic_proxy")
        j_klass = CQPEnv().FindClass(cls_name).global_ref()
        cls_dict["_chaquopy_j_klass"] = j_klass

        if ("." in cls_name) and ("[" not in cls_name):
            module, _, simple_name = cls_name.rpartition(".")
        else:
            module, simple_name = "", cls_name
        cls_dict["__module__"] = module

        if bases is None:  # When called from jclass()
            klass = Class(instance=j_klass)
            superclass, interfaces = klass.getSuperclass(), klass.getInterfaces()
            if not (superclass or interfaces):  # Class is a top-level interface
                superclass = JavaObject.getClass()
            bases = [jclass(k.getName()) for k in
                     ([superclass] if superclass else []) + interfaces]
            bases.sort(cmp=lambda a, b: -1 if issubclass(a, b) else 1 if issubclass(b, a) else 0)

        cls = type.__new__(metacls, simple_name, tuple(bases), cls_dict)
        jclass_cache[cls_name] = cls
        return cls

    # We do this in JavaClass.__call__ rather than JavaObject.__new__ because there's no way
    # for __new__ to prevent __init__ from being called or to modify its arguments, and
    # __init__ may be overridden by user-defined proxy classes.
    def __call__(cls, *args, JNIRef instance=None, **kwargs):
        self = None
        if instance:
            assert not (args or kwargs)
            with class_lock:
                self = instance_cache.get((cls, instance))  # Include cls in key because of cast()
                if not self:
                    env = CQPEnv()
                    if not env.IsInstanceOf(instance, cls._chaquopy_j_klass):
                        expected = java.sig_to_java(klass_sig(env, cls._chaquopy_j_klass))
                        actual = java.sig_to_java(object_sig(env, instance))
                        raise TypeError(f"cannot create {expected} proxy from {actual} instance")
                    self = cls.__new__(cls, *args, **kwargs)
                    set_this(self, instance.global_ref(),
                             cast=(env.GetObjectClass(instance) != cls._chaquopy_j_klass))
        else:
            self = type.__call__(cls, *args, **kwargs)  # May block

        return self

    # Override to allow static field set (type.__setattr__ would simply overwrite the class dict)
    def __setattr__(cls, name, value):
        member = type_lookup(cls, name)
        if isinstance(member, JavaMember):
            member.__set__(None, value)
        else:
            type.__setattr__(cls, name, value)


def setup_object_class():
    global JavaObject
    class JavaObject(six.with_metaclass(JavaClass, object)):
        _chaquopy_name = "java.lang.Object"

        def __init__(self, *args):
            # Java SE 8 raises an InstantiationException when calling NewObject on an abstract
            # class, but Android 6 crashes with a CheckJNI error.
            if Modifier.isAbstract(self.getClass().getModifiers()):
                raise TypeError(f"{cls_fullname(type(self))} is abstract and cannot be instantiated")

            # Can't use getattr(): Java constructors are not inherited.
            try:
                constructor = type(self).__dict__["<init>"]
            except KeyError:
                raise TypeError(f"{cls_fullname(type(self))} has no accessible constructors")
            set_this(self, constructor.__get__(self, type(self))(*args))

        def __setattr__(self, name, value):
            # Using __slots__ to prevent adding attributes is unreliable, as it's defeated by
            # any base class which provides a __dict__. For example, Python Exception objects
            # have a __dict__, so that would cause all Java Throwables to have one too.
            object.__setattr__(self, name, value)
            if (name in self.__dict__) and not name.startswith("_chaquopy"):
                del self.__dict__[name]
                # Exception type and wording are based on Python 2.7.
                raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        def __repr__(self):
            full_name = cls_fullname(type(self))
            if self._chaquopy_this:
                ts = self.toString()
                if ts is not None and \
                   ts.startswith(full_name):  # e.g. "java.lang.Object@28d93b30"
                    return f"<{ts}>"
                else:
                    return f"<{full_name} '{ts}'>"
            else:
                return f"<{full_name} (no instance)>"

        def __str__(self):       return self.toString()
        def __hash__(self):      return self.hashCode()
        def __eq__(self, other): return self.equals(other)
        def __ne__(self, other): return not (self == other)  # Not automatic in Python 2

        @classmethod    # To provide the equivalent of Java ".class" syntax
        def getClass(cls):
            return Class(instance=cls._chaquopy_j_klass)


# Associates a Python object with its Java counterpart.
#
# Making _chaquopy_this a WeakRef avoids a cross-language reference cycle for static and
# dynamic proxies. The destruction sequence for Java objects is as follows:
#
#     * The Python object dies.
#     * (PROXY ONLY) The object __dict__ is kept alive by a PyObject reference from the Java
#       object. If the Java object is ever accessed by Python again, this allows the object's
#       Python state to be recovered and attached to a new Python object.
#     * The GlobalRef for the Java object is removed from instance_cache.
#     * The Java object dies once there are no Java references to it.
#     * (PROXY ONLY) The WeakRef is now invalid, but that's not a problem because it's
#       unreachable from both languages. With the Java object gone, the __dict__ and WeakRef
#       now die, in that order.
def set_this(self, GlobalRef this, *, cast=False):
    with class_lock:
        self._chaquopy_this = this.weak_ref()
        self._chaquopy_cast = cast
        instance_cache[(type(self), this)] = self

        if "PyProxy" in globals() and isinstance(self, PyProxy):
            java_dict = self._chaquopyGetDict()
            if java_dict is None:
                self._chaquopySetDict(self.__dict__)
            else:
                self.__dict__ = java_dict


# This isn't done during module initialization because we don't have a JVM yet, and we don't
# want to automatically start one because we might already be in a Java process.
def setup_bootstrap_classes():
    # Declare only the methods needed to complete the bootstrap process.
    global Class, Modifier, Method, Field, Constructor
    if "Class" in globals():
        raise Exception("setup_bootstrap_classes called more than once")

    setup_object_class()

    AnnotatedElement = jclass_proxy("java.lang.reflect.AnnotatedElement", [JavaObject])
    AccessibleObject = jclass_proxy("java.lang.reflect.AccessibleObject",
                                    [AnnotatedElement, JavaObject])
    Member = jclass_proxy("java.lang.reflect.Member", [JavaObject])
    GenericDeclaration = jclass_proxy("java.lang.reflect.GenericDeclaration", [JavaObject])

    Class = jclass_proxy("java.lang.Class", [AnnotatedElement, GenericDeclaration, JavaObject])
    add_member(Class, "getDeclaredClasses", JavaMethod('()[Ljava/lang/Class;'))
    add_member(Class, "getDeclaredConstructors", JavaMethod('()[Ljava/lang/reflect/Constructor;'))
    add_member(Class, "getDeclaredFields", JavaMethod('()[Ljava/lang/reflect/Field;'))
    add_member(Class, "getDeclaredMethods", JavaMethod('()[Ljava/lang/reflect/Method;'))
    add_member(Class, "getName", JavaMethod('()Ljava/lang/String;'))

    Modifier = jclass_proxy("java.lang.reflect.Modifier", [JavaObject])
    add_member(Modifier, "isAbstract", JavaMethod('(I)Z', static=True))
    add_member(Modifier, "isFinal", JavaMethod('(I)Z', static=True))
    add_member(Modifier, "isPublic", JavaMethod('(I)Z', static=True))
    add_member(Modifier, "isStatic", JavaMethod('(I)Z', static=True))

    Method = jclass_proxy("java.lang.reflect.Method", [AccessibleObject, GenericDeclaration, Member])
    add_member(Method, "getModifiers", JavaMethod('()I'))
    add_member(Method, "getName", JavaMethod('()Ljava/lang/String;'))
    add_member(Method, "getParameterTypes", JavaMethod('()[Ljava/lang/Class;'))
    add_member(Method, "getReturnType", JavaMethod('()Ljava/lang/Class;'))
    add_member(Method, "isSynthetic", JavaMethod('()Z'))
    add_member(Method, "isVarArgs", JavaMethod('()Z'))

    Field = jclass_proxy("java.lang.reflect.Field", [AccessibleObject, Member])
    add_member(Field, "getModifiers", JavaMethod('()I'))
    add_member(Field, "getName", JavaMethod('()Ljava/lang/String;'))
    add_member(Field, "getType", JavaMethod('()Ljava/lang/Class;'))

    Constructor = jclass_proxy("java.lang.reflect.Constructor",
                               [AccessibleObject, GenericDeclaration, Member])
    add_member(Constructor, "getModifiers", JavaMethod('()I'))
    add_member(Constructor, "getName", JavaMethod('()Ljava/lang/String;'))
    add_member(Constructor, "getParameterTypes", JavaMethod('()[Ljava/lang/Class;'))
    add_member(Constructor, "isSynthetic", JavaMethod('()Z'))
    add_member(Constructor, "isVarArgs", JavaMethod('()Z'))

    global Cloneable, Serializable  # See array.pxi
    Cloneable = jclass_proxy("java.lang.Cloneable", [JavaObject])
    Serializable = jclass_proxy("java.io.Serializable", [JavaObject])

    for cls in [JavaObject, AnnotatedElement, AccessibleObject, Member, GenericDeclaration,
                Class, Modifier, Method, Field, Constructor, Cloneable, Serializable]:
        reflect_class(cls)

    Throwable = jclass_proxy("java.lang.Throwable", [JavaException, Serializable, JavaObject])
    reflect_class(Throwable)

    global ClassLoader, Proxy, PyInvocationHandler, PyProxy
    ClassLoader = jclass("java.lang.ClassLoader")
    Proxy = jclass("java.lang.reflect.Proxy")
    PyInvocationHandler = jclass("com.chaquo.python.PyInvocationHandler")
    PyProxy = jclass("com.chaquo.python.PyProxy")


def reflect_class(cls):
    klass = cls.getClass()

    name_key = lambda m: m.getName()
    all_methods = [m for m in chain(klass.getDeclaredMethods(), klass.getDeclaredConstructors())
                   if Modifier.isPublic(m.getModifiers())]
    all_methods.sort(key=name_key)
    for name, methods in groupby(all_methods, name_key):
        jms = []
        for method in methods:
            if isinstance(method, Constructor):
                name = "<init>"
            if method.isSynthetic():
                # isSynthetic returns true in the following relevant cases:
                #  * Where a method override has identical parameter types but a covariant (i.e.
                #    subclassed) return type, the JVM will not consider it to be an override.
                #    So the compiler also generates a forwarding "bridge" method with the
                #    original return type.
                continue
            jms.append(JavaMethod(method))

        # To speed up reflection, we avoid checking signatures here. This means we'll create
        # JavaMultipleMethods for all methods which are overridden in this class, even if
        # they're not overloaded. JavaMultipleMethod.resolve will tidy up the situation the
        # first time the method is used.
        for ancestor in cls.__mro__[1:]:
            try:
                inherited = ancestor.__dict__.get(name)
            except KeyError: continue
            if isinstance(inherited, JavaMethod):
                jms.append(inherited)
            elif isinstance(inherited, JavaMultipleMethod):
                jms += (<JavaMultipleMethod?>inherited).methods
            break

        add_member(cls, name, jms[0] if (len(jms) == 1) else JavaMultipleMethod(jms))

    for field in klass.getDeclaredFields():
        # TODO #5183 method hides field with same name.
        add_member(cls, field.getName(), JavaField(field))

    for nested_klass in klass.getDeclaredClasses():
        name = nested_klass.getSimpleName()  # Returns empty string for anonymous classes.
        if name:
            # TODO #5261 add a JavaMember subclass which delays the jclass call
            add_member(cls, name, jclass(nested_klass.getName()))

    aliases = {}
    for name, member in six.iteritems(cls.__dict__):
        # As recommended by PEP 8, members whose names are reserved words can be accessed by
        # appending an underscore. The original name is still accessible via getattr().
        if is_reserved_word(name):
            aliases[name + "_"] =  member
    for alias, member in six.iteritems(aliases):
        if alias not in cls.__dict__:
            add_member(cls, alias, member)


# Ensure the same aliases are available on all Python versions
EXTRA_RESERVED_WORDS = {'exec', 'print',                      # Removed in Python 3.0
                        'nonlocal', 'True', 'False', 'None',  # Added in Python 3.0
                        'async', 'await'}                     # Added in Python 3.5

def is_reserved_word(word):
    return keyword.iskeyword(word) or word in EXTRA_RESERVED_WORDS


# Looks up an attribute in a class hierarchy without calling descriptors.
def type_lookup(cls, name):
    for c in cls.__mro__:
        try:
            return c.__dict__[name]
        except KeyError: pass
    return None


def add_member(cls, name, member):
    if name not in cls.__dict__:  # TODO #5183 method hides field with same name.
        type.__setattr__(cls, name, member)  # Direct modification of cls.__dict__ is not allowed.
        if isinstance(member, JavaMember):
            member.added_to_class(cls, name)


cdef class JavaMember(object):
    cdef cls
    cdef basestring name

    def __set__(self, obj, value):
        raise AttributeError(f"Java member {self.fqn()} is not a field")

    def added_to_class(self, cls, name):
        if not self.cls:  # May be called a second time for a reserved word alias.
            self.cls = cls
            self.name = name

    def fqn(self):
        return f"{cls_fullname(self.cls)}.{self.name}"


cdef class JavaSimpleMember(JavaMember):
    cdef reflected
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
            self.is_static = Modifier.isStatic(self.reflected.getModifiers())


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
        cdef JNIRef j_klass = self.cls._chaquopy_j_klass
        if self.is_static:
            self.j_field = env.GetStaticFieldID(j_klass, self.name, self.definition)
        else:
            self.j_field = env.GetFieldID(j_klass, self.name, self.definition)

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
        cdef jobject j_class = (<JNIRef?>self.cls._chaquopy_j_klass).obj
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
        cdef jobject j_class = (<JNIRef?>self.cls._chaquopy_j_klass).obj
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
    cdef bint is_abstract
    cdef bint is_varargs

    def __repr__(self):
        self.resolve()
        return f"<JavaMethod {self.java_declaration()}>"

    def java_declaration(self):
        return (f"{'static ' if self.is_static else ''}"
                f"{java.sig_to_java(self.definition_return)} {self.fqn()}"
                f"{java.args_sig_to_java(self.definition_args, self.is_varargs)}")

    def __init__(self, definition_or_reflected, *, static=False, varargs=False, abstract=False):
        super().__init__(definition_or_reflected, static=static)
        self.is_varargs = varargs
        self.is_abstract = abstract

    def resolve(self):
        if self.j_method: return

        super().resolve()
        if self.reflected:
            return_type = (java.jvoid if isinstance(self.reflected, Constructor)
                           else self.reflected.getReturnType())
            self.definition = java.jni_method_sig(return_type, self.reflected.getParameterTypes())
            self.is_varargs = self.reflected.isVarArgs()
            self.is_abstract = Modifier.isAbstract(self.reflected.getModifiers())

        env = CQPEnv()
        cdef JNIRef j_klass = self.cls._chaquopy_j_klass
        if self.is_static:
            self.j_method = env.GetStaticMethodID(j_klass, self.name, self.definition)
        else:
            self.j_method = env.GetMethodID(j_klass, self.name, self.definition)
        self.definition_return, self.definition_args = java.split_method_sig(self.definition)
        self.is_constructor = (self.name == "<init>")

    # To be consistent with Python syntax, we want instance methods to be called non-virtually
    # in the following cases:
    #
    #   * When the method is got from a class rather than an instance. This is easy to detect:
    #     obj is None.
    #   * When the method is got via a super() object. Unfortunately I don't think there's any
    #     way to detect this: objtype is set to the first parameter of super(), which in the
    #     common case is just type(obj).
    #
    # So we have to take the opposite approach and consider when methods *must* be called
    # virtually. The only case I can think of is when we're using cast() to hide overloads
    # added in a subclass, but we still want to call the subclass overrides of visible
    # overloads. So we'll call virtually whenever the method is got from a cast object.
    # Otherwise we'll call non-virtually, and rely on the Python method resolution rules to
    # pick the correct override.
    def __get__(self, obj, objtype):
        self.resolve()
        if obj is None or self.is_static or self.is_constructor:
            return self
        else:
            return lambda *args: self(obj, *args, virtual=obj._chaquopy_cast)

    def __call__(self, *args, virtual=False):
        cdef jvalue *j_args = NULL
        cdef tuple d_args = self.definition_args
        env = CQPEnv()

        if self.is_abstract and virtual is False:
            raise NotImplementedError(f"{self.fqn()} is abstract and cannot be called directly")

        if self.is_static or self.is_constructor:
            obj = None
        else:
            obj, args = self.get_this(args)

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

        p2j_args = [p2j(env.j_env, argtype, arg)
                    for argtype, arg in six.moves.zip(d_args, args)]
        if len(args):
            j_args = <jvalue*>alloca(sizeof(jvalue) * len(d_args))
            populate_args(env.j_env, d_args, j_args, p2j_args)

        if self.is_constructor:
            result = self.call_constructor(env.j_env, j_args)
        elif self.is_static:
            result = self.call_static_method(env, j_args)
        elif virtual:
            result = self.call_virtual_method(env, obj._chaquopy_this, j_args)
        else:
            result = self.call_nonvirtual_method(env, obj._chaquopy_this, j_args)

        copy_output_args(d_args, args, p2j_args)
        return result

    # Exception types and wording are based on Python 2.7.
    cdef get_this(self, args):
        if not args:
            got = "nothing"
        else:
            obj = args[0]
            if isinstance(obj, self.cls):
                return obj, args[1:]
            else:
                got = f"{type(obj).__name__} instance"
        raise TypeError(f"Unbound method {self.fqn()} must be called with {cls_fullname(self.cls)} "
                        f"instance as first argument (got {got} instead)")

    cdef GlobalRef call_constructor(self, JNIEnv *j_env, jvalue *j_args):
        cdef jobject j_self
        cdef JNIRef j_klass = self.cls._chaquopy_j_klass
        with nogil:
            j_self = j_env[0].NewObjectA(j_env, j_klass.obj, self.j_method, j_args)
        check_exception(j_env)
        return LocalRef.adopt(j_env, j_self).global_ref()

    cdef call_virtual_method(self, CQPEnv env, JNIRef this, jvalue *j_args):
        r = self.definition_return[0]
        if r == 'V':
            env.CallVoidMethodA(this, self.j_method, j_args)
        elif r == 'Z':
            return env.CallBooleanMethodA(this, self.j_method, j_args)
        elif r == 'B':
            return env.CallByteMethodA(this, self.j_method, j_args)
        elif r == 'C':
            return env.CallCharMethodA(this, self.j_method, j_args)
        elif r == 'S':
            return env.CallShortMethodA(this, self.j_method, j_args)
        elif r == 'I':
            return env.CallIntMethodA(this, self.j_method, j_args)
        elif r == 'J':
            return env.CallLongMethodA(this, self.j_method, j_args)
        elif r == 'F':
            return env.CallFloatMethodA(this, self.j_method, j_args)
        elif r == 'D':
            return env.CallDoubleMethodA(this, self.j_method, j_args)
        elif r in 'L[':
            return j2p(env.j_env, env.CallObjectMethodA(this, self.j_method, j_args))
        else:
            raise Exception(f"Invalid definition for {self.fqn()}: '{self.definition_return}'")

    cdef call_nonvirtual_method(self, CQPEnv env, JNIRef this, jvalue *j_args):
        cdef JNIRef j_klass = self.cls._chaquopy_j_klass
        r = self.definition_return[0]
        if r == 'V':
            env.CallNonvirtualVoidMethodA(this, j_klass, self.j_method, j_args)
        elif r == 'Z':
            return env.CallNonvirtualBooleanMethodA(this, j_klass, self.j_method, j_args)
        elif r == 'B':
            return env.CallNonvirtualByteMethodA(this, j_klass, self.j_method, j_args)
        elif r == 'C':
            return env.CallNonvirtualCharMethodA(this, j_klass, self.j_method, j_args)
        elif r == 'S':
            return env.CallNonvirtualShortMethodA(this, j_klass, self.j_method, j_args)
        elif r == 'I':
            return env.CallNonvirtualIntMethodA(this, j_klass, self.j_method, j_args)
        elif r == 'J':
            return env.CallNonvirtualLongMethodA(this, j_klass, self.j_method, j_args)
        elif r == 'F':
            return env.CallNonvirtualFloatMethodA(this, j_klass, self.j_method, j_args)
        elif r == 'D':
            return env.CallNonvirtualDoubleMethodA(this, j_klass, self.j_method, j_args)
        elif r in 'L[':
            return j2p(env.j_env, env.CallNonvirtualObjectMethodA(this, j_klass, self.j_method,
                                                                  j_args))
        else:
            raise Exception(f"Invalid definition for {self.fqn()}: '{self.definition_return}'")

    cdef call_static_method(self, CQPEnv env, jvalue *j_args):
        cdef JNIRef j_klass = self.cls._chaquopy_j_klass
        r = self.definition_return[0]
        if r == 'V':
            env.CallStaticVoidMethodA(j_klass, self.j_method, j_args)
        elif r == 'Z':
            return env.CallStaticBooleanMethodA(j_klass, self.j_method, j_args)
        elif r == 'B':
            return env.CallStaticByteMethodA(j_klass, self.j_method, j_args)
        elif r == 'C':
            return env.CallStaticCharMethodA(j_klass, self.j_method, j_args)
        elif r == 'S':
            return env.CallStaticShortMethodA(j_klass, self.j_method, j_args)
        elif r == 'I':
            return env.CallStaticIntMethodA(j_klass, self.j_method, j_args)
        elif r == 'J':
            return env.CallStaticLongMethodA(j_klass, self.j_method, j_args)
        elif r == 'F':
            return env.CallStaticFloatMethodA(j_klass, self.j_method, j_args)
        elif r == 'D':
            return env.CallStaticDoubleMethodA(j_klass, self.j_method, j_args)
        elif r in 'L[':
            return j2p(env.j_env, env.CallStaticObjectMethodA(j_klass, self.j_method, j_args))
        else:
            raise Exception(f"Invalid definition for {self.fqn()}: '{self.definition_return}'")


cdef class JavaMultipleMethod(JavaMember):
    cdef list methods
    cdef dict overload_cache
    cdef bint resolved

    def __repr__(self):
        self.resolve()
        return f"<JavaMultipleMethod {self.methods}>"

    def __init__(self, methods):
        self.methods = methods
        self.overload_cache = {}

    def added_to_class(self, cls, name):
        super().added_to_class(cls, name)
        cdef JavaMethod jm
        for jm in self.methods:
            jm.added_to_class(cls, name)

    def resolve(self):
        if self.resolved: return

        sigs_seen = set()
        overridden = []
        cdef JavaMethod jm
        for jm in self.methods:
            jm.resolve()
            if jm.definition_args in sigs_seen:
                overridden.append(jm)
            else:
                sigs_seen.add(jm.definition_args)

        # See comment in reflect_class
        for jm in overridden:
            self.methods.remove(jm)
        if len(self.methods) == 1:
            type.__setattr__(self.cls, self.name, self.methods[0])

        self.resolved = True

    def __get__(self, obj, objtype):
        self.resolve()
        return lambda *args: self(obj, objtype, *args)

    def __call__(self, obj, objtype, *args):
        args_types = tuple(map(type, args))
        obj_args_types = (type(obj), args_types)
        best_overload = self.overload_cache.get(obj_args_types)
        if not best_overload:
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
            env = CQPEnv()
            maximal = []
            for jm1 in applicable:
                if not any([better_overload(env, jm2, jm1, args_types, varargs=varargs)
                            for jm2 in applicable if jm2 is not jm1]):
                    maximal.append(jm1)
            if len(maximal) != 1:
                raise TypeError(self.overload_err(f"is ambiguous for arguments", args,
                                                  maximal if maximal else applicable))
            best_overload = maximal[0]
            self.overload_cache[obj_args_types] = best_overload

        return best_overload.__get__(obj, objtype)(*args)

    def find_applicable(self, obj, args, *, autobox, varargs):
        result = []
        cdef JavaMethod jm
        for jm in self.methods:
            if obj is None and not (jm.is_static or jm.is_constructor):  # Unbound method
                # TODO #5265 ambiguity still possible if isinstance() returns True but args[0]
                # was intended as the first parameter of a static overload.
                if not (args and isinstance(args[0], self.cls)):
                    continue
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
                ", ".join([jm.java_declaration() for jm in methods]))
