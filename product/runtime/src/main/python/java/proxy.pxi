# Proxy objects can have user-defined Python attributes, so remove the restrictions imposed
# by JavaObject.__setattr__.
global_class("com.chaquo.python.PyProxy", cls_dict={"__setattr__": object.__setattr__})


PROXY_BASE_NAME = "_chaquopy_proxy"


class ProxyClass(JavaClass):
    def __new__(metacls, cls_name, bases, cls_dict):
        if cls_name == PROXY_BASE_NAME:
            return type.__new__(metacls, cls_name, bases, cls_dict)
        else:
            if not (bases and bases[0].__name__ == PROXY_BASE_NAME):
                raise TypeError(f"{metacls.proxy_func} must be used first in class bases")
            if any([b.__name__ == PROXY_BASE_NAME for b in bases[1:]]):
                raise TypeError(f"{metacls.proxy_func} can only be used once in class bases")

            klass = metacls.get_klass(cls_name, bases[0])
            cls_dict["_chaquopy_j_klass"] = klass._chaquopy_this
            cls_dict["_chaquopy_name"] = klass.getName()
            cls = JavaClass.__new__(metacls, cls_name,
                                    get_bases(klass) + bases[1:],
                                    cls_dict)

            # We can't use reflect_class, because to avoid infinite recursion, we need
            # unimplemented methods (including those from java.lang.Object) to fall through in
            # Python to the inherited members.
            metacls.add_constructors(cls)
            for method in cls.getClass().getDeclaredMethods():
                name = method.getName()
                if name.startswith("_chaquopy"):  # See set_this in class.pxi, and PyInvocationHandler
                    add_member(cls, name, JavaMethod(method))

            return cls


# -------------------------------------------------------------------------------------------------


global_class("java.lang.reflect.Proxy")
global_class("com.chaquo.python.PyInvocationHandler")


def dynamic_proxy(*implements):
    """Use the return value of this function in the bases of a class declaration, and the
    `java.lang.reflect.Proxy
    <https://docs.oracle.com/javase/7/docs/api/java/lang/reflect/Proxy.html>`_ mechanism will
    be used to generate a Java class for it at runtime. All arguments must be Java interface
    types.
    """
    for i in implements:
        if not (isinstance(i, type) and issubclass(i, JavaObject) and
                i.getClass().isInterface()):
            raise TypeError(f"{i!r} is not a Java interface")
    return DynamicProxyClass(PROXY_BASE_NAME, (), dict(implements=implements))


class DynamicProxyClass(ProxyClass):
    proxy_func = "dynamic_proxy"

    def __call__(cls, *args, JNIRef instance=None, **kwargs):
        self = JavaClass.__call__(cls, *args, instance=instance, **kwargs)
        if instance:
            # jclass_cache will contain the most recently-created Python class for the given
            # sequence of interfaces, but the Python-Java class mapping may be many-to-one.
            actual_cls = self._chaquopyGetType()
            if actual_cls is not cls:
                self = actual_cls(instance=instance)
        return self

    @classmethod
    def get_klass(metacls, cls_name, proxy_base):
        global DynamicProxy
        return Proxy.getProxyClass(DynamicProxy.getClass().getClassLoader(),
                                   (DynamicProxy,) + proxy_base.implements)

    @classmethod
    def add_constructors(metacls, cls):
        add_member(cls, "<init>", JavaMethod("(Ljava/lang/reflect/InvocationHandler;)V"))


def DynamicProxy_init(self):
    global PyInvocationHandler
    JavaObject.__init__(self, PyInvocationHandler(type(self)))

global_class("com.chaquo.python.DynamicProxy", cls_dict={"__init__": DynamicProxy_init})


# -------------------------------------------------------------------------------------------------


global_class("com.chaquo.python.PyCtorMarker")

def static_proxy(extends=None, *implements, package=None, modifiers="public"):
    """Use the return value of this function in the bases of a class declaration, and the
    :ref:`static proxy generator <static-proxy-generator>` tool will create a Java source file
    allowing the class to be instantiated and accessed by Java code. `extends` must be a Java
    class, or None for `java.lang.Object`. `implements`, if present, must be Java interface
    types. `package` is the name of the Java package in which the Java class will be generated,
    defaulting to the same as the Python module name.

    Extending static_proxy classes with other static_proxy classes is not currently supported.
    However, behaviour can still be shared between static_proxy classes by making them inherit from
    a common Python base class.
    """
    if extends is None:
        extends = JavaObject
    if package is None:
        # _getframe(0) returns the closest Python frame, ignoring Cython frames.
        package = sys._getframe(0).f_globals["__name__"]
    return StaticProxyClass(PROXY_BASE_NAME, (), dict(extends=extends, implements=implements,
                                                      package=package))

class StaticProxyClass(ProxyClass):
    proxy_func = "static_proxy"

    @classmethod
    def get_klass(metacls, cls_name, proxy_base):
        global StaticProxy
        java_name = proxy_base.package + "." + cls_name
        klass = Class(instance=CQPEnv().FindClass(java_name))

        def verify(what, expected, actual):
            if expected != actual:
                raise TypeError(f"expected {what} {expected}, but Java class actually "
                                f"{what} {actual}")
        verify("extends", proxy_base.extends.getClass().getName(), klass.getSuperclass().getName())
        verify("implements",
               [str(i.getClass().getName()) for i in proxy_base.implements + (StaticProxy,)],
               [str(i.getName()) for i in klass.getInterfaces()])
        return klass

    @classmethod
    def add_constructors(metacls, cls):
        add_member(cls, "<init>", JavaMethod("(Lcom/chaquo/python/PyCtorMarker;)V"))


def StaticProxy_init(self):
    global PyCtorMarker
    if hasattr(self, "_chaquopy_this"):     # Java-initiated construction
        pass
    else:                                   # Python-initiated construction
        JavaObject.__init__(self, PyCtorMarker())

global_class("com.chaquo.python.StaticProxy", cls_dict={"__init__": StaticProxy_init})


# Member decorators currently have no effect at runtime.
def constructor(arg_types, *, modifiers="public", throws=None):
    """Generates a Java constructor. This decorator can only be used on the `__init__` method.
    """
    return lambda f: f
def method(return_type, arg_types, *, modifiers="public", throws=None):
    """Generates a Java method.
    """
    return lambda f: f
def Override(return_type, arg_types, *, modifiers="public", throws=None):
    """Same as :any:`method`, but adds the `@Override
    <https://docs.oracle.com/javase/8/docs/api/java/lang/Override.html>`_ annotation.
    """
    return lambda f: f
