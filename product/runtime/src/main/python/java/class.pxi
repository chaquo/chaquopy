from collections import defaultdict
from itertools import chain, groupby
import keyword
from threading import RLock
from weakref import WeakValueDictionary


global_class("java.lang.ClassNotFoundException")
global_class("java.lang.NoClassDefFoundError")
global_class("java.lang.reflect.InvocationTargetException")


class_lock = RLock()
jclass_cache = {}
instance_cache = WeakValueDictionary()


# TODO #5167 this may fail in non-Java-created threads on Android, because they'll use the
# wrong ClassLoader.
def jclass(clsname, **kwargs):
    """Returns a Python class for a Java class or interface type. The name must be fully-qualified,
    using either Java notation (e.g. `java.lang.Object`) or JNI notation (e.g.
    `Ljava/lang/Object;`). To refer to a nested or inner class, separate it from the containing
    class with `$`, e.g. `java.lang.Map$Entry`.

    If the class cannot be found, a `NoClassDefFoundError` is raised.
    """
    if clsname.startswith("["):
        return jarray(clsname[1:])
    if clsname in java.primitives_by_name:
        raise ValueError("Cannot reflect a primitive type")
    if clsname.startswith("L") and clsname.endswith(";"):
        clsname = clsname[1:-1]
    clsname = clsname.replace('/', '.')

    if not isinstance(clsname, str):
        clsname = str(clsname)

    with class_lock:
        global ClassNotFoundException, NoClassDefFoundError
        cls = jclass_cache.get(clsname)
        if not cls:
            try:
                cls = jclass_proxy(clsname, **kwargs)
            except Exception as e:
                # Putting this directly in an `except` clause would cause any other exception
                # to be hidden by a NameError if ClassNotFoundException isn't defined yet.
                if "ClassNotFoundException" in globals() and isinstance(e, ClassNotFoundException):
                    # Java SE 8 throws NoClassDefFoundError like the JNI spec says, but Android 6
                    # throws ClassNotFoundException. Hide this from our users.
                    ncdfe = NoClassDefFoundError(e.getMessage())
                    ncdfe.setStackTrace(e.getStackTrace())
                    raise ncdfe
                else:
                    raise
            reflect_class(cls)
        return cls


def jclass_proxy(cls_name, bases=None, *, cls_dict=None):
    if not isinstance(bases, (tuple, type(None))):
        bases = tuple(bases)
    if cls_dict is None:
        cls_dict = {}
    cls_dict["_chaquopy_name"] = cls_name
    return JavaClass(None, bases, cls_dict)


class JavaClass(type):
    def __new__(metacls, cls_name, bases, cls_dict):
        java_name = cls_dict.pop("_chaquopy_name", None)
        if not java_name:
            raise TypeError("Java classes can only be inherited using static_proxy or dynamic_proxy")

        if "_chaquopy_j_klass" not in cls_dict:
            cls_dict["_chaquopy_j_klass"] = CQPEnv().FindClass(java_name).global_ref()
            if ("." in java_name) and ("[" not in java_name):
                module, _, cls_name = java_name.rpartition(".")
            else:
                module, cls_name = "", java_name
            cls_dict["__module__"] = module

        if bases is None:  # When called from jclass()
            klass = Class(instance=cls_dict["_chaquopy_j_klass"])
            bases = get_bases(klass) + cls_dict.pop("_chaquopy_post_bases", ())
            if ("StaticProxy" in globals()) and (StaticProxy in bases):
                raise TypeError(f"static_proxy class {java_name} loaded before its Python "
                                f"counterpart")

        cls = type.__new__(metacls, cls_name, bases, cls_dict)
        jclass_cache[java_name] = cls
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

                    actual_j_klass = env.GetObjectClass(instance)
                    if actual_j_klass == cls._chaquopy_j_klass:
                        real_obj = None  # Setting to `self` would cause a reference cycle with self.__dict__.
                    else:
                        real_sig = klass_sig(env, actual_j_klass)
                        real_obj = jclass(real_sig)(instance=instance)
                    set_this(self, instance.global_ref(), real_obj)
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


def get_bases(klass):
    superclass, interfaces = klass.getSuperclass(), klass.getInterfaces()
    if not (superclass or interfaces):  # Class is a top-level interface
        superclass = JavaObject.getClass()
    bases = [jclass(k.getName()) for k in
             ([superclass] if superclass else []) + interfaces]

    # Produce a valid order for the C3 MRO algorithm, if one exists.
    bases.sort(cmp=lambda a, b: (-1 if issubclass(a, b)
                                 else 1 if issubclass(b, a)
                                 else 0))
    return tuple(bases)


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

        def __getattr__(self, name):
            if name.startswith("_chaquopy"):
                raise AttributeError(f"'{type(self).__name__}' object's superclass __init__ must "
                                     "be called before using it as a Java object")
            else:
                object.__getattribute__(self, name)  # Should raise AttributeError
                raise AttributeError(f"__getattribute__({name!r}) unexpectedly succeeded")

        def __setattr__(self, name, value):
            # We can't use __slots__ to prevent adding attributes, because Throwable inherits
            # from the (Python) Exception class, which causes two problems:
            #   * Exception is a native class, so multiple inheritance with anything which has
            #     __slots__ is impossible ("multiple bases have instance lay-out conflict").
            #   * Exception has a __dict__, which would cause all Java Throwables to have one too.
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
                    return f"<{full_name} {str_repr(ts)}>"
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
# Making _chaquopy_this a weak reference avoids a cross-language reference cycle for static and
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
def set_this(self, GlobalRef this, real_obj=None):
    global PyProxy
    with class_lock:
        self._chaquopy_this = this.weak_ref()  # TODO for non-proxy objects we can just use `this`.
        self._chaquopy_real_obj = real_obj
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
    add_member(Class, "getModifiers", JavaMethod('()I'))
    add_member(Class, "getName", JavaMethod('()Ljava/lang/String;'))

    Modifier = jclass_proxy("java.lang.reflect.Modifier", [JavaObject])
    add_member(Modifier, "isAbstract", JavaMethod('(I)Z', static=True))
    add_member(Modifier, "isFinal", JavaMethod('(I)Z', static=True))
    add_member(Modifier, "isProtected", JavaMethod('(I)Z', static=True))
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

    # Arrays will be required for reflect_class, and `jarray` gives arrays these interfaces.
    global Cloneable, Serializable
    Cloneable = jclass_proxy("java.lang.Cloneable", [JavaObject])
    Serializable = jclass_proxy("java.io.Serializable", [JavaObject])

    for cls in [JavaObject, AnnotatedElement, AccessibleObject, Member, GenericDeclaration,
                Class, Modifier, Method, Field, Constructor, Cloneable, Serializable]:
        reflect_class(cls)

    load_global_classes()


def reflect_class(cls):
    klass = cls.getClass()
    all_methods = filter(is_accessible, chain(klass.getDeclaredMethods(),
                                              klass.getDeclaredConstructors()))
    name_key = lambda m: m.getName()
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

    for field in filter(is_accessible, klass.getDeclaredFields()):
        # TODO #5183 method hides field with same name.
        add_member(cls, field.getName(), JavaField(field))

    for nested_klass in filter(is_accessible, klass.getDeclaredClasses()):
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


# Protected members need to be accessible to static proxy classes, but we can't practically do
# that without making them accessible everywhere. Technically package members should be
# accessible as well if the static proxy is generated in the same package, but we'll leave that
# for now.
def is_accessible(member):
    mods = member.getModifiers()
    return Modifier.isPublic(mods) or Modifier.isProtected(mods)


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
    cdef bint is_final

    def __init__(self, definition_or_reflected, static, final):
        if isinstance(definition_or_reflected, str):
            self.definition = definition_or_reflected
        else:
            self.reflected = definition_or_reflected
        self.is_static = static
        self.is_final = final

    def resolve(self):
        if self.reflected:
            self.is_static = Modifier.isStatic(self.reflected.getModifiers())
            self.is_final = Modifier.isFinal(self.reflected.getModifiers())

    def format_modifiers(self):
        return (f"{'static ' if self.is_static else ''}"
                f"{'final ' if self.is_final else ''}")


cdef class JavaField(JavaSimpleMember):
    cdef jfieldID j_field

    def __repr__(self):
        self.resolve()
        return (f"<JavaField {self.format_modifiers()}"
                f"{java.sig_to_java(self.definition)} {self.fqn()}>")

    def __init__(self, definition_or_reflected, *, static=False, final=False):
        super().__init__(definition_or_reflected, static, final)

    def resolve(self):
        if self.j_field: return

        super().resolve()
        if self.reflected:
            self.definition = java.jni_sig(self.reflected.getType())

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
    cdef basestring return_sig
    cdef tuple args_sig
    cdef bint is_constructor
    cdef bint is_abstract
    cdef bint is_varargs

    def __repr__(self):
        self.resolve()
        return f"<JavaMethod {self.format_declaration()}>"

    def format_declaration(self):
        return (f"{self.format_modifiers()}"
                f"{java.sig_to_java(self.return_sig)} {self.fqn()}"
                f"{java.args_sig_to_java(self.args_sig, self.is_varargs)}")

    def __init__(self, definition_or_reflected, *, static=False, varargs=False, abstract=False,
                 final=False):
        super().__init__(definition_or_reflected, static, final)
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
        self.return_sig, self.args_sig = java.split_method_sig(self.definition)
        self.is_constructor = (self.name == "<init>")

    # To be consistent with Python syntax, we want instance methods to be called non-virtually
    # in the following cases:
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
            return lambda *args: self(obj, *args, virtual=(obj._chaquopy_real_obj is not None))

    def __call__(self, *args, virtual=False):
        # Check this up front, because the "unbound method" error that check_args would give
        # would be misleading for an abstract method.
        if self.is_abstract and not virtual:
            raise NotImplementedError(f"{self.fqn()} is abstract and cannot be called")

        env = CQPEnv()
        obj, args = self.check_args(args)
        p2j_args = [p2j(env.j_env, argtype, arg)
                    for argtype, arg in six.moves.zip(self.args_sig, args)]

        if self.is_constructor:
            result = self.call_constructor(env, p2j_args)
        elif self.is_static:
            result = self.call_static_method(env, p2j_args)
        elif virtual:
            result = self.call_virtual_method(env, obj, p2j_args)
        else:
            result = self.call_nonvirtual_method(env, obj, p2j_args)

        copy_output_args(self.args_sig, args, p2j_args)
        return result

    # Exception types and wording are based on Python 2.7.
    def check_args(self, args):
        obj = None
        if not (self.is_static or self.is_constructor):
            if not args:
                got_wrong = "nothing"
            else:
                obj = args[0]
                if isinstance(obj, self.cls):
                    got_wrong = None
                    args = args[1:]
                else:
                    got_wrong = f"{type(obj).__name__} instance"
            if got_wrong:
                raise TypeError(f"Unbound method {self.fqn()} must be called with "
                                f"{cls_fullname(self.cls)} instance as first argument "
                                f"(got {got_wrong} instead)")

        if self.is_varargs:
            if len(args) < len(self.args_sig) - 1:
                raise TypeError(f'{self.fqn()} takes at least '
                                f'{plural(len(self.args_sig) - 1, "argument")} ({len(args)} given)')

            if len(args) == len(self.args_sig) and assignable_to_array(self.args_sig[-1], args[-1]):
                # As in Java, passing a single None as the varargs parameter will be
                # interpreted as a null array. To pass an an array of one null, use [None].
                pass  # Non-varargs call.
            else:
                args = args[:len(self.args_sig) - 1] + (args[len(self.args_sig) - 1:],)
        if len(args) != len(self.args_sig):
            raise TypeError(f'{self.fqn()} takes {plural(len(self.args_sig), "argument")} '
                            f'({len(args)} given)')
        return obj, args

    cdef GlobalRef call_constructor(self, CQPEnv env, p2j_args):
        cdef jvalue *j_args = <jvalue*>alloca(sizeof(jvalue) * len(p2j_args))
        populate_args(self, p2j_args, j_args)
        return env.NewObjectA(self.cls._chaquopy_j_klass, self.j_method, j_args).global_ref()

    cdef call_virtual_method(self, CQPEnv env, obj, p2j_args):
        global Proxy
        if "Proxy" in globals() and \
           isinstance(obj._chaquopy_real_obj or obj, Proxy) and \
           not (self.cls is JavaObject and self.is_final):  # See comment at call_proxy_method
            return self.call_proxy_method(env, obj, p2j_args)

        cdef JNIRef this = obj._chaquopy_this
        cdef jvalue *j_args = <jvalue*>alloca(sizeof(jvalue) * len(p2j_args))
        populate_args(self, p2j_args, j_args)

        r = self.return_sig[0]
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
            raise Exception(f"Invalid definition for {self.fqn()}: '{self.return_sig}'")

    cdef call_nonvirtual_method(self, CQPEnv env, obj, p2j_args):
        if "Proxy" in globals() and issubclass(self.cls, Proxy):
            return self.call_proxy_method(env, obj, p2j_args)

        cdef JNIRef this = obj._chaquopy_this
        cdef JNIRef j_klass = self.cls._chaquopy_j_klass
        cdef jvalue *j_args = <jvalue*>alloca(sizeof(jvalue) * len(p2j_args))
        populate_args(self, p2j_args, j_args)

        r = self.return_sig[0]
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
            raise Exception(f"Invalid definition for {self.fqn()}: '{self.return_sig}'")

    # Android API levels 23 and higher have at least two bugs causing native crashes when
    # calling proxy methods through JNI. This affects all the methods of the interfaces passed
    # to Proxy.getProxyClass, and all the non-final methods of Object. Full details are in
    # #5274, but the outcome is:
    #   * We cannot use CallNonvirtual...Method on a proxy method.
    #   * We cannot use Call...Method if it will resolve to a proxy method.
    #
    # Luckily, calls through Method.invoke appear to be unaffected.
    cdef call_proxy_method(self, CQPEnv env, obj, p2j_args):
        for i, (arg_sig, p2j_arg) in enumerate(six.moves.zip(self.args_sig, p2j_args)):
            box_cls_name = PRIMITIVE_TYPES.get(arg_sig)
            if box_cls_name:
                p2j_args[i] = jclass(f"java.lang.{box_cls_name}")(p2j_arg)._chaquopy_this

        global InvocationTargetException
        try:
            return self.reflected.invoke(obj, [JavaObject(instance=r) for r in p2j_args])
        except InvocationTargetException as e:
            raise e.getCause()

    cdef call_static_method(self, CQPEnv env, p2j_args):
        cdef JNIRef j_klass = self.cls._chaquopy_j_klass
        cdef jvalue *j_args = <jvalue*>alloca(sizeof(jvalue) * len(p2j_args))
        populate_args(self, p2j_args, j_args)

        r = self.return_sig[0]
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
            raise Exception(f"Invalid definition for {self.fqn()}: '{self.return_sig}'")


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
            if jm.args_sig in sigs_seen:
                overridden.append(jm)
            else:
                sigs_seen.add(jm.args_sig)

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
               is_applicable(jm.args_sig, args_except_this, autobox, varargs):
                result.append(jm)
        return result

    def overload_err(self, msg, args, methods):
        args_type_names = "({})".format(", ".join([type(a).__name__ for a in args]))
        return (f"{self.fqn()} {msg} {args_type_names}: options are " +
                ", ".join([jm.format_declaration() for jm in methods]))
