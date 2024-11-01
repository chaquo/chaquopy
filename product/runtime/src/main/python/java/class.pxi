import keyword
from threading import RLock
from weakref import WeakValueDictionary

global_class("java.lang.ClassNotFoundException")
global_class("java.lang.NoClassDefFoundError")
global_class("java.lang.reflect.InvocationTargetException")


cdef class_lock = RLock()
cdef dict jclass_cache = {}
cdef instance_cache = WeakValueDictionary()
# class_lock also protects none_casts in utils.pxi.

# Attributes which will never be looked up as Java members. This prevents infinite recursion, and is
# also important for performance.
cdef set special_attrs = set(dir(type) +                        # Special Python attributes
                             ["_chaquopy_j_klass",              # Chaquopy class attributes
                              "_chaquopy_reflector",            #
                              "_chaquopy_sam_name",             #
                              "_chaquopy_this",                 # Chaquopy instance attributes
                              "_chaquopy_real_obj"])            #


# If you already have a Class object, use one of these functions rather than calling `jclass`
# directly. This avoids looking up the class by name, which doesn't work with lambda classes on
# the Oracle JVM.
cdef jclass_from_klass(klass):
    return jclass_from_j_klass(klass.getName(), klass._chaquopy_this)

cdef jclass_from_j_klass(cls_name, JNIRef j_klass):
    return jclass(cls_name, {"_chaquopy_j_klass": j_klass.global_ref()})

cpdef jclass(clsname, cls_dict=None):
    """Returns a Python class for a Java class or interface type. The name must be fully-qualified,
    using either Java notation (e.g. `java.lang.Object`) or JNI notation (e.g.
    `Ljava/lang/Object;`). To refer to a nested or inner class, separate it from the containing
    class with `$`, e.g. `java.lang.Map$Entry`.

    If the class cannot be found, a `NoClassDefFoundError` is raised.
    """
    if clsname.startswith("["):
        return jarray(clsname[1:])
    if clsname in primitives_by_name:
        raise ValueError("Cannot reflect a primitive type")
    if clsname.startswith("L") and clsname.endswith(";"):
        clsname = clsname[1:-1]
    clsname = clsname.replace('/', '.')

    if not isinstance(clsname, str):
        clsname = str(clsname)

    with class_lock:
        cls = jclass_cache.get(clsname)
        if cls:
            # Can't alter class dict after class has been reflected.
            assert (cls_dict is None) or (list(cls_dict) == ["_chaquopy_j_klass"]), clsname
        else:
            cls = new_class(clsname, None, cls_dict)
        return cls


cdef new_class(cls_name, bases, cls_dict=None):
    if cls_dict is None:
        cls_dict = {}
    cls_dict["_chaquopy_name"] = cls_name
    return JavaClass(None, bases, cls_dict)


# This isn't a cdef class because that would make it more difficult to use as a metaclass.
# TODO: see if this is still true on the current version of Python.
class JavaClass(type):
    def __new__(metacls, cls_name, bases, cls_dict):
        java_name = cls_dict.pop("_chaquopy_name", None)
        if not java_name:
            raise TypeError("Java classes can only be inherited using static_proxy or dynamic_proxy")

        if "_chaquopy_j_klass" not in cls_dict:
            cls_dict["_chaquopy_j_klass"] = CQPEnv().FindClass(java_name)

        # For a proxy class, we should leave __name__ and __module__ set to the Python-level
        # values the user would expect.
        if not issubclass(metacls, ProxyClass):
            if "[" in java_name:
                module, cls_name = "java", f"jarray('{java_name[1:]}')"
            elif "." in java_name:
                module, _, cls_name = java_name.rpartition(".")
            else:
                module, cls_name = "", java_name
            cls_dict["__module__"] = module

        if bases is None:  # When called from jclass()
            klass = Class(instance=cls_dict["_chaquopy_j_klass"])
            bases = get_bases(klass) + cls_dict.pop("_chaquopy_post_bases", ())
            if (StaticProxy is not None) and (StaticProxy in bases):
                raise TypeError(f"static_proxy class {java_name} loaded before its Python "
                                f"counterpart")

        cls = type.__new__(metacls, cls_name, bases, cls_dict)
        cls.__qualname__ = cls.__name__  # Otherwise repr(Object) would contain "JavaObject".
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
                if self is None:
                    env = CQPEnv()
                    if not env.IsInstanceOf(instance, cls._chaquopy_j_klass):
                        expected = sig_to_java(klass_sig(env, cls._chaquopy_j_klass))
                        actual = sig_to_java(object_sig(env, instance))
                        raise TypeError(f"cannot create {expected} proxy from {actual} instance")
                    self = cls.__new__(cls, *args, **kwargs)

                    actual_j_klass = env.GetObjectClass(instance)
                    if actual_j_klass == cls._chaquopy_j_klass:
                        real_obj = None  # Setting to `self` would cause a reference cycle with self.__dict__.
                    else:
                        real_sig = klass_sig(env, actual_j_klass)
                        real_cls = jclass(real_sig)
                        assert actual_j_klass == real_cls._chaquopy_j_klass, (
                            # https://github.com/Electron-Cash/Electron-Cash/issues/1692
                            f"when instantiating {cls}, signature '{real_sig}' returned "
                            f"{real_cls} with j_klass {real_cls._chaquopy_j_klass}, which differs "
                            f"from instance j_klass {actual_j_klass}")
                        real_obj = real_cls(instance=instance)
                    set_this(self, instance.global_ref(), real_obj)
        else:
            self = type.__call__(cls, *args, **kwargs)  # May block

        return self

    def __getattribute__(cls, str name):
        if not (name in special_attrs or name in type_dict(cls)):
            reflect_member(cls, name)
        return type.__getattribute__(cls, name)

    # Override to allow static field set (type.__setattr__ would simply overwrite the class dict)
    def __setattr__(cls, str name, value):
        if not (name in special_attrs or name in type_dict(cls)):
            reflect_member(cls, name)
        member = type_lookup(cls, name)
        if isinstance(member, JavaMember):
            member.__set__(None, value)
        else:
            type.__setattr__(cls, name, value)

    def __dir__(cls):
        result = set(super().__dir__())
        for c in cls.__mro__:
            if isinstance(c, JavaClass) and not isinstance(c, ProxyClass):
                result.update([str(s) for s in get_reflector(c).dir()])
        return list(result)


cdef get_bases(klass):
    superklass = klass.getSuperclass()
    superclass = jclass_from_klass(superklass) if superklass else None
    interfaces = [jclass_from_klass(i) for i in klass.getInterfaces()]
    if not (superclass or interfaces):  # Class is a top-level interface
        superclass = JavaObject

    # Java gives us the interfaces in declaration order, but Python requires them to be in
    # topological order.
    bases = []
    while interfaces:
        free = [i1 for i1 in interfaces
                if all([(i2 is i1) or (not issubclass(i2, i1))
                        for i2 in interfaces])]
        assert free, interfaces
        # To allow diamond inheritance, ancestor order must also be consistent (see
        # test_inheritance_order).
        free.sort(key=lambda cls: [m.__name__ for m in reversed(cls.__mro__)])
        bases.append(free[0])
        interfaces.remove(free[0])

    # Superclass must be positioned for correct method resolution order (see
    # reflect_member and #1205).
    if superclass:
        bases.insert(len(bases) if superclass is JavaObject else 0,
                     superclass)
    return tuple(bases)


cdef setup_object_class():
    # We probably can't make this a cdef class, because we need (Java) Throwable to inherit from
    # both JavaObject and (Python) Exception, which is *also* a native class. Multiple inheritance
    # from two native classes would give a "multiple bases have instance lay-out conflict" error.
    global JavaObject
    class JavaObject(metaclass=JavaClass):
        _chaquopy_name = "java.lang.Object"

        def __init__(self, *args):
            # Java SE 8 raises an InstantiationException when calling NewObject on an abstract
            # class, but Android 6 crashes with a CheckJNI error.
            if Modifier.isAbstract(type(self).getClass().getModifiers()):
                raise TypeError(f"{cls_fullname(type(self))} is abstract and cannot be instantiated")

            # Can't use getattr(): Java constructors are not inherited.
            constructor = reflect_member(type(self), "<init>", inherit=False)
            if not constructor:
                raise TypeError(f"{cls_fullname(type(self))} has no accessible constructors")
            set_this(self, constructor.__get__(self, type(self))(*args))

        def __getattribute__(self, str name):
            cls = type(self)
            if not (name in special_attrs or name in type_dict(cls)):
                reflect_member(cls, name)
            try:
                return object.__getattribute__(self, name)
            except AttributeError:
                if name.startswith("_chaquopy"):
                    raise AttributeError(f"'{type(self).__name__}' object's superclass __init__ must "
                                         "be called before using it as a Java object")
                else:
                    raise

        def __setattr__(self, str name, value):
            cls = type(self)
            if not (name in special_attrs or name in type_dict(cls)):
                reflect_member(cls, name)

            # We can't use __slots__ to prevent adding attributes, because Throwable inherits
            # from the (Python) Exception class, which causes two problems:
            #   * Exception is a native class, so multiple inheritance with anything which has
            #     __slots__ is impossible ("multiple bases have instance lay-out conflict").
            #   * Exception has a __dict__, which would cause all Java Throwables to have one too.
            object.__setattr__(self, name, value)
            if (name in self.__dict__) and not name.startswith("_chaquopy") and \
               not isinstance(type(self), ProxyClass):
                del self.__dict__[name]
                raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        def __dir__(self):
            result = set(dir(type(self)))
            result.update(self.__dict__)
            return list(result)

        def __repr__(self):
            full_name = cls_fullname(type(self))
            if self._chaquopy_this:
                ts = self.toString()
                if ts is None:
                    return f"<{full_name} [toString returned null]>"
                elif ts.startswith(full_name):  # e.g. "java.lang.Object@28d93b30"
                    return f"<{ts}>"
                else:
                    return f"<{full_name} '{ts}'>"
            else:
                return f"<{full_name} [no instance]>"

        def __str__(self):       return self.toString()
        def __hash__(self):      return self.hashCode()
        def __eq__(self, other): return self.equals(other)

        def __reduce_ex__(self, protocol):
            import pickle  # Delay import so we don't need to add _pickle to the bootstrap list.
            raise pickle.PicklingError("Java objects cannot be pickled")

        def __call__(self, *args):
            cls = type(self)
            sam_name = type_dict(cls).get("_chaquopy_sam_name", None)
            if sam_name is None:
                sam_name = cls._chaquopy_sam_name = get_sam(cls).getName()
            return getattr(self, sam_name)(*args)


# If the class implements exactly one functional interface, returns the Method object of the
# single abstract method (SAM). Otherwise, throws TypeError.
def get_sam(cls):
    def signature(m):
        return (m.getName(), tuple(m.getParameterTypes()))

    object_methods = {signature(m) for m in JavaObject.getClass().getMethods()}

    # Kotlin lambdas and method references implement the functional interface
    # kotlin.jvm.functions.FunctionN, where N is the number of arguments. However, they also
    # implement some other interfaces which just happen to be functional, so ignore them. The
    # Gradle plugin provides a ProGuard file which stops these names from being minified.
    ignored_interfaces = {
        "kotlin.jvm.internal.FunctionBase",
        "kotlin.reflect.KAnnotatedElement"
    }

    sams = {}
    for mro_cls in cls.__mro__:
        if isinstance(mro_cls, JavaClass):
            klass = mro_cls.getClass()
            if klass.isInterface() and (klass.getName() not in ignored_interfaces):
                methods = [m for m in klass.getMethods()
                           if (Modifier.isAbstract(m.getModifiers()) and
                               signature(m) not in object_methods)]
                if len(methods) == 1:
                    sams[signature(methods[0])] = methods[0]
                    if mro_cls is cls:
                        # If a jclass object is of an interface type, it must have been created
                        # using `cast`, so give that interface priority over its ancestors.
                        break

    if len(sams) == 0:
        raise TypeError(f"{cls.__name__} is not callable because it implements no "
                        f"functional interfaces")
    elif len(sams) == 1:
        return sams.popitem()[1]
    else:
        interfaces = ", ".join([sam.getDeclaringClass().getName()
                                for sam in sams.values()])
        raise TypeError(f"{cls.__name__} implements multiple functional interfaces "
                        f"({interfaces}): use cast() to select one")


# Associates a Python object with its Java counterpart.
#
# Making _chaquopy_this a WeakRef for proxy objects avoids a cross-language reference
# cycle. The destruction sequence for Java objects is as follows:
#
#     * The Python object dies.
#     * (PROXY ONLY) The object __dict__ is kept alive by a PyObject reference from the Java
#       object. If the Java object is ever accessed by Python again, this allows the object's
#       Python state to be recovered and attached to a new Python object.
#     * The GlobalRef for the Java object is removed from instance_cache.
#     * The Java object dies once there are no Java references to it.
#     * (PROXY ONLY) The WeakRef in the __dict__ is now invalid, but that's not a
#       problem because the __dict__ is unreachable from both languages. With the Java object
#       gone, the __dict__ and WeakRef now die, in that order.
cdef set_this(self, GlobalRef this, real_obj=None):
    global PyProxy
    with class_lock:
        is_proxy = isinstance(type(self), ProxyClass)
        self._chaquopy_this = this.weak_ref() if is_proxy else this
        self._chaquopy_real_obj = real_obj
        instance_cache[(type(self), this)] = self

        if is_proxy:
            java_dict = self._chaquopyGetDict()
            if java_dict is None:
                self._chaquopySetDict(self.__dict__)
            else:
                self.__dict__ = java_dict


# This isn't done during module initialization because we don't have a JVM yet, and we don't
# want to automatically start one because we might already be in a Java process.
cdef setup_bootstrap_classes():
# Declare only the methods needed to complete the bootstrap process.
    global Reflector, Class, Modifier, Method, Field, Constructor
    if "Class" in globals():
        raise Exception("setup_bootstrap_classes called more than once")

    setup_object_class()

    Reflector = new_class("com.chaquo.python.Reflector", (JavaObject,))
    bootstrap_method(Reflector, "getInstance",
                     "(Ljava/lang/Class;)Lcom/chaquo/python/Reflector;", static=True)
    bootstrap_method(Reflector, "getMethods",
                     "(Ljava/lang/String;)[Ljava/lang/reflect/Member;")
    bootstrap_method(Reflector, "getField", "(Ljava/lang/String;)Ljava/lang/reflect/Field;")
    bootstrap_method(Reflector, "getNestedClass", "(Ljava/lang/String;)Ljava/lang/Class;")

    AnnotatedElement = new_class("java.lang.reflect.AnnotatedElement", (JavaObject,))
    AccessibleObject = new_class("java.lang.reflect.AccessibleObject",
                                 (AnnotatedElement, JavaObject))
    Member = new_class("java.lang.reflect.Member", (JavaObject,))
    GenericDeclaration = new_class("java.lang.reflect.GenericDeclaration", (JavaObject,))

    Class = new_class("java.lang.Class", (AnnotatedElement, GenericDeclaration, JavaObject))
    bootstrap_method(Class, "getModifiers", '()I')
    bootstrap_method(Class, "getName", '()Ljava/lang/String;')

    Modifier = new_class("java.lang.reflect.Modifier", (JavaObject,))
    bootstrap_method(Modifier, "isAbstract", '(I)Z', static=True)
    bootstrap_method(Modifier, "isFinal", '(I)Z', static=True)
    bootstrap_method(Modifier, "isStatic", '(I)Z', static=True)

    Method = new_class("java.lang.reflect.Method",
                       (AccessibleObject, GenericDeclaration, Member))
    bootstrap_method(Method, "getModifiers", '()I')
    bootstrap_method(Method, "getName", '()Ljava/lang/String;')
    bootstrap_method(Method, "getParameterTypes", '()[Ljava/lang/Class;')
    bootstrap_method(Method, "getReturnType", '()Ljava/lang/Class;')
    bootstrap_method(Method, "isVarArgs", '()Z')

    Field = new_class("java.lang.reflect.Field", (AccessibleObject, Member))
    bootstrap_method(Field, "getModifiers", '()I')
    bootstrap_method(Field, "getName", '()Ljava/lang/String;')
    bootstrap_method(Field, "getType", '()Ljava/lang/Class;')

    Constructor = new_class("java.lang.reflect.Constructor",
                            (AccessibleObject, GenericDeclaration, Member))
    bootstrap_method(Constructor, "getModifiers", '()I')
    bootstrap_method(Constructor, "getName", '()Ljava/lang/String;')
    bootstrap_method(Constructor, "getParameterTypes", '()[Ljava/lang/Class;')
    bootstrap_method(Constructor, "isVarArgs", '()Z')

    # Arrays will be required for class reflection, and `jarray` gives arrays these interfaces.
    global Cloneable, Serializable
    Cloneable = new_class("java.lang.Cloneable", (JavaObject,))
    Serializable = new_class("java.io.Serializable", (JavaObject,))

    load_global_classes()


cdef bootstrap_method(cls, name, signature, static=False):
    member = JavaMethod(cls, name, signature, static=static)
    type.__setattr__(cls, name, member)  # Direct modification of cls.__dict__ is blocked.


# If the class has a declared or inherited Java member of the given name, this function ensures it's
# in cls.__dict__, and then returns it. Otherwise it returns None.
cdef reflect_member(cls, str name, bint inherit=True):
    try:
        return type_dict(cls)[name]
    except KeyError: pass

    inherited = None
    if inherit:
        for base in cls.__bases__:
            if issubclass(base, JavaObject):
                inherited = reflect_member(base, name)
                if isinstance(inherited, JavaMember):
                    # TODO #1205: do interface default methods require us to handle
                    # multiple inheritance?
                    break

    # To avoid infinite recursion, we need unimplemented methods in proxy classes (including
    # those from java.lang.Object) to fall through in Python to the inherited members.
    if isinstance(cls, ProxyClass):
        member = inherited
    else:
        member = find_member(cls, name, inherited)
    if member:
        # Direct modification of cls.__dict__ is blocked, and we can't set via type_dict either: see
        # comment there.
        type.__setattr__(cls, name, member)
        return member

    # As recommended by PEP 8, members whose names are reserved words are available through dot
    # notation by appending an underscore. The original name is still accessible via getattr().
    if name.endswith("_") and is_reserved_word(name[:-1]):
        member = reflect_member(cls, name[:-1], inherit=inherit)
        if member:
            type.__setattr__(cls, name, member)
            return member


cdef find_member(cls, name, inherited=None):
    reflector = get_reflector(cls)
    jms = [JavaMethod(cls, name, m) for m in (reflector.getMethods(name) or [])]
    if isinstance(inherited, JavaMethod):
        jms.append(inherited)
    elif isinstance(inherited, JavaMultipleMethod):
        jms += (<JavaMultipleMethod?>inherited).methods
    if jms:
        jms = apply_overrides(jms)
        return jms[0] if (len(jms) == 1) else JavaMultipleMethod(cls, name, jms)

    field = reflector.getField(name)
    if field:
        return JavaField(cls, name, field)

    nested = reflector.getNestedClass(name)
    if nested:
        return jclass(nested.getName())

    return inherited


cdef get_reflector(cls):
    reflector = cls.__dict__.get("_chaquopy_reflector")
    if not reflector:
        # Can't call constructor directly, because JavaObject.__init__ calls some inherited
        # methods which would themselves require a Reflector to resolve.
        reflector = Reflector.getInstance(Class(instance=cls.__dict__["_chaquopy_j_klass"]))
        type.__setattr__(cls, "_chaquopy_reflector", reflector)
    return reflector


# Methods earlier in the list will override later ones with the same argument signature.
cdef apply_overrides(jms_in):
    jms_out = []
    sigs_seen = set()
    cdef JavaMethod jm
    for jm in jms_in:
        if jm.args_sig not in sigs_seen:
            jms_out.append(jm)
            sigs_seen.add(jm.args_sig)
    return jms_out


# For backward compatibility, keep generating aliases for words which are no longer reserved in
# the current version of Python.
EXTRA_RESERVED_WORDS = {'exec', 'print'}                      # Removed in Python 3.0

cdef is_reserved_word(word):
    return keyword.iskeyword(word) or word in EXTRA_RESERVED_WORDS


# Looks up an attribute in a class hierarchy without calling descriptors.
cdef type_lookup(cls, name):
    for c in cls.__mro__:
        try:
            return c.__dict__[name]
        except KeyError: pass
    return None


cdef class JavaMember(object):
    cdef cls
    cdef basestring name

    def __init__(self, cls, name):
        self.cls = cls
        self.name = name

    def __set__(self, obj, value):
        raise AttributeError(f"Java member {self.fqn()} is not a field")

    cdef fqn(self):
        return f"{cls_fullname(self.cls)}.{self.name}"


cdef class JavaSimpleMember(JavaMember):
    cdef bint is_static
    cdef bint is_final

    def __init__(self, cls, name, static, final):
        super().__init__(cls, name)
        self.is_static = static
        self.is_final = final

    cdef format_modifiers(self):
        return (f"{'static ' if self.is_static else ''}"
                f"{'final ' if self.is_final else ''}")


cdef class JavaField(JavaSimpleMember):
    cdef basestring definition
    cdef jfieldID j_field

    def __repr__(self):
        return (f"<JavaField {self.format_modifiers()}"
                f"{sig_to_java(self.definition)} {self.fqn()}>")

    def __init__(self, cls, name, definition_or_reflected, *, static=False, final=False):
        if isinstance(definition_or_reflected, str):
            self.definition = definition_or_reflected
        else:
            reflected = definition_or_reflected
            self.definition = jni_sig(reflected.getType())
            modifiers = reflected.getModifiers()
            static = Modifier.isStatic(modifiers)
            final = Modifier.isFinal(modifiers)
        super().__init__(cls, name, static, final)

        env = CQPEnv()
        cdef JNIRef j_klass = self.cls._chaquopy_j_klass
        if self.is_static:
            self.j_field = env.GetStaticFieldID(j_klass, self.name, self.definition)
        else:
            self.j_field = env.GetFieldID(j_klass, self.name, self.definition)

    def __get__(self, obj, objtype):
        if self.is_static:
            return self.read_static_field()
        else:
            if obj is None:
                raise AttributeError(f'Cannot access {self.fqn()} in static context')
            return self.read_field(obj)

    def __set__(self, obj, value):
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
            return chr(j_env[0].GetCharField(j_env, j_self, self.j_field))
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
            return chr(j_env[0].GetStaticCharField(j_env, j_class, self.j_field))
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
    cdef reflected  # See call_proxy_method
    cdef jmethodID j_method
    cdef basestring return_sig
    cdef tuple args_sig  # Can't be a list: it's used as a set key in apply_overrides.
    cdef bint is_constructor
    cdef bint is_abstract
    cdef bint is_varargs

    def __repr__(self):
        return f"<JavaMethod {self.format_declaration()}>"

    cdef format_declaration(self):
        return (f"{self.format_modifiers()}"
                f"{sig_to_java(self.return_sig)} {self.fqn()}"
                f"{args_sig_to_java(self.args_sig, self.is_varargs)}")

    def __init__(self, cls, name, definition_or_reflected, *, static=False, final=False,
                 abstract=False, varargs=False):
        self.is_constructor = (name == "<init>")
        if isinstance(definition_or_reflected, str):
            definition = definition_or_reflected
            self.return_sig, self.args_sig = split_method_sig(definition)
        else:
            self.reflected = definition_or_reflected
            self.return_sig = ("V" if self.is_constructor
                               else jni_sig(self.reflected.getReturnType()))
            self.args_sig = tuple([jni_sig(x) for x in self.reflected.getParameterTypes()])
            definition = f"({''.join(self.args_sig)}){self.return_sig}"
            modifiers = self.reflected.getModifiers()
            static = Modifier.isStatic(modifiers)
            final = Modifier.isFinal(modifiers)
            abstract = Modifier.isAbstract(modifiers)
            varargs = self.reflected.isVarArgs()

        super().__init__(cls, name, static, final)
        self.is_abstract = abstract
        self.is_varargs = varargs

        env = CQPEnv()
        cdef JNIRef j_klass = self.cls._chaquopy_j_klass
        if self.is_static:
            self.j_method = env.GetStaticMethodID(j_klass, self.name, definition)
        else:
            self.j_method = env.GetMethodID(j_klass, self.name, definition)

    # To be consistent with Python syntax, we want instance methods to be called non-virtually
    # in the following cases:
    #   * When the method is got from a class rather than an instance. This is easy to detect:
    #     obj is None.
    #   * When the method is got via a super() object. Unfortunately I don't think there's any
    #     way to detect this: objtype is set to the first parameter of super(), which in the
    #     common case is just type(obj). (TODO: this comment is out of date, since we don't
    #     support super() anymore except in constructors.)
    #
    # So we have to take the opposite approach and consider when methods *must* be called
    # virtually. The only case I can think of is when we're using cast() to hide overloads
    # added in a subclass, but we still want to call the subclass overrides of visible
    # overloads. So we'll call virtually whenever the method is got from a cast object.
    # Otherwise we'll call non-virtually, and rely on the Python method resolution rules to
    # pick the correct override. (TODO: this comment is also out of date, because
    # reflect_member bypasses the Python method resolution rules.)
    def __get__(self, obj, objtype):
        if obj is None and self.name == "getClass":  # Equivalent of Java `.class` syntax.
            return lambda: Class(instance=objtype._chaquopy_j_klass)
        elif obj is None or self.is_static or self.is_constructor:
            return self
        else:
            return lambda *args: self(obj, *args, virtual=(obj._chaquopy_real_obj is not None))

    def __call__(self, *args, virtual=False):
        # Check this up front, because the "unbound method" error that check_args would give
        # would be misleading for an abstract method.
        if self.is_abstract and not virtual:
            raise NotImplementedError(f"{self.fqn()} is abstract and cannot be called")

        env = CQPEnv()
        obj, args = self.check_args(env, args)
        p2j_args = [p2j(env.j_env, argtype, arg)
                    for argtype, arg in zip(self.args_sig, args)]

        if self.is_constructor:
            result = self.call_constructor(env, p2j_args)
        elif self.is_static:
            result = self.call_static_method(env, p2j_args)
        elif virtual:
            result = self.call_virtual_method(env, obj, p2j_args)
        else:
            result = self.call_nonvirtual_method(env, obj, p2j_args)

        copy_output_args(env, args, p2j_args)
        return result

    cdef check_args(self, CQPEnv env, args):
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

            if len(args) == len(self.args_sig) and \
               assignable_to_array(env, self.args_sig[-1], args[-1]):
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
        if (Proxy is not None) and isinstance(obj._chaquopy_real_obj or obj, Proxy) and \
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
        if (Proxy is not None) and issubclass(self.cls, Proxy):
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

    # Android API levels 23 and higher sometimes experience native crashes when calling
    # proxy methods through JNI. This affects all the methods of the interfaces passed
    # to Proxy.getProxyClass, and all the non-final methods of Object. Full details are
    # in https://issuetracker.google.com/issues/64871880, but the outcome is:
    #   * We cannot use the CallNonvirtual... functions on a proxy method.
    #   * We cannot use the virtual Call... functions on a method which resolves to a
    #     proxy method (fixed in API level 25, at least when the method is obtained from
    #     one of the proxy class's interfaces as opposed to the class itself).
    #   * So instead, we make the call through Method.invoke.
    cdef call_proxy_method(self, CQPEnv env, obj, p2j_args):
        for i, (arg_sig, p2j_arg) in enumerate(zip(self.args_sig, p2j_args)):
            box_cls_name = PRIMITIVE_TYPES.get(arg_sig)
            if box_cls_name:
                p2j_args[i] = jclass(f"java.lang.{box_cls_name}")(p2j_arg)._chaquopy_this

        global InvocationTargetException
        try:
            return self.reflected.invoke(obj, [JavaObject(instance=r) for r in p2j_args])
        except InvocationTargetException as e:
            # Avoid creating an exception chain which would double the error message size while
            # adding no useful information.
            raise e.getCause() from None

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

    def __repr__(self):
        return f"<JavaMultipleMethod {self.methods}>"

    def __init__(self, cls, name, methods):
        super().__init__(cls, name)
        self.methods = methods
        self.overload_cache = {}

    def __get__(self, obj, objtype):
        return lambda *args: self(obj, objtype, *args)

    def __call__(self, obj, objtype, *args):
        args_types = tuple(map(type, args))
        obj_args_types = (type(obj), args_types)
        best_overload = self.overload_cache.get(obj_args_types)
        if not best_overload:
            env = CQPEnv()

            # JLS 15.12.2.2. "Identify Matching Arity Methods Applicable by Subtyping"
            varargs = False
            applicable = self.find_applicable(env, obj, args, autobox=False, varargs=False)

            # JLS 15.12.2.3. "Identify Matching Arity Methods Applicable by Method Invocation
            # Conversion"
            if not applicable:
                applicable = self.find_applicable(env, obj, args, autobox=True, varargs=False)

            # JLS 15.12.2.4. "Identify Applicable Variable Arity Methods"
            if not applicable:
                varargs = True
                applicable = self.find_applicable(env, obj, args, autobox=True, varargs=True)

            if not applicable:
                raise TypeError(self.overload_err(f"cannot be applied to", args, self.methods))

            # JLS 15.12.2.5. "Choosing the Most Specific Method"
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

    cdef find_applicable(self, CQPEnv env, obj, args, autobox, varargs):
        result = []
        cdef JavaMethod jm
        for jm in self.methods:
            if obj is None and not (jm.is_static or jm.is_constructor):  # Unbound method
                # TODO #1208 ambiguity still possible if isinstance() returns True but
                # args[0] was intended as the first parameter of a static overload.
                if not (args and isinstance(args[0], self.cls)):
                    continue
                args_except_this = args[1:]
            else:
                args_except_this = args
            if not (varargs and not jm.is_varargs) and \
               is_applicable(env, jm.args_sig, args_except_this, autobox, varargs):
                result.append(jm)
        return result

    cdef overload_err(self, msg, args, methods):
        cdef JavaMethod jm
        args_type_names = "({})".format(", ".join([type(a).__name__ for a in args]))
        return (f"{self.fqn()} {msg} {args_type_names}: options are " +
                ", ".join([jm.format_declaration() for jm in methods]))
