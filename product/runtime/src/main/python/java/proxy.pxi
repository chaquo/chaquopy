PROXY_BASE_NAME = "_chaquopy_proxy"


def dynamic_proxy(*interfaces):
    return DynamicProxyClass(PROXY_BASE_NAME, tuple(interfaces), {})

class DynamicProxyClass(JavaClass):
    def __new__(metacls, cls_name, bases, cls_dict):
        global ClassLoader, Proxy, PyInvocationHandler
        if "PyInvocationHandler" not in globals():
            ClassLoader = jclass("java.lang.ClassLoader")
            Proxy = jclass("java.lang.reflect.Proxy")
            PyInvocationHandler = jclass("com.chaquo.python.PyInvocationHandler")

        if cls_name == PROXY_BASE_NAME:
            for b in bases:
                if not (isinstance(b, type) and issubclass(b, JavaObject) and
                        b.getClass().isInterface()):
                    raise TypeError(f"{b!r} is not a Java interface")
            return type.__new__(metacls, cls_name, bases, cls_dict)

        else:
            if not (bases and bases[0].__name__ == PROXY_BASE_NAME):
                raise TypeError("dynamic_proxy must be used first in class bases")
            if any([b.__name__ == PROXY_BASE_NAME for b in bases[1:]]):
                raise TypeError("dynamic_proxy can only be used once in class bases")
            klass = Proxy.getProxyClass(ClassLoader.getSystemClassLoader(), *(bases[0].__bases__))
            cls_dict["_chaquopy_j_klass"] = klass._chaquopy_this
            cls = type.__new__(metacls, cls_name,
                               (DynamicProxy,) + bases[0].__bases__ + bases[1:],
                               cls_dict)
            jclass_cache[klass.getName()] = cls
            return cls


# TODO: Python proxy objects should also be isinstance(java.lang.reflect.Proxy), maybe by a
# similar mechanism to Throwable.
class DynamicProxy(object):
    def __init__(self):
        cls = type(self)
        if "<init>" not in cls.__dict__:
            add_member(cls, "<init>", JavaMethod("(Ljava/lang/reflect/InvocationHandler;)V"))
        JavaObject.__init__(self, PyInvocationHandler(dict()))

    def __getattr__(self, name):
        if name == "_chaquopy_this":
            raise AttributeError("dynamic_proxy superclass __init__ must be called before "
                                 "accessing attributes")
        elif name == "_chaquopy_dict":
            self.__dict__[name] = Proxy.getInvocationHandler(self)._chaquopyGetDict()
            return self.__dict__[name]
        else:
            try:
                return self._chaquopy_dict[name]
            except KeyError:
                raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        try:
            JavaObject.__setattr__(self, name, value)
        except ReadOnlyAttributeError:
            raise
        except AttributeError:
            self._chaquopy_dict[name] = value
