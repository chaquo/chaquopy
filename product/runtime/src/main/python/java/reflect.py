from __future__ import absolute_import, division, print_function
from six import with_metaclass

import java
from .chaquopy import CQPEnv, JavaObject, JavaClass, JavaMethod, JavaField, JavaMultipleMethod
from .signatures import *

__all__ = ['jclass']


jclass_cache = {}


# This isn't done during module initialization because we don't have a JVM yet, and we don't
# want to automatically start one because we might already be in a Java process.
def setup_bootstrap_classes():
    if "Constructor" in globals():  # Last class to be defined
        return

    # Declare only the members used by reflect_class or anything it calls.
    # Generated with the help of runtime/make_proxy.py
    global Class, Modifier, Method, Field, Constructor

    class Class(with_metaclass(JavaClass, JavaObject)):
        __javaclass__ = 'java.lang.Class'
        getConstructors = JavaMethod('()[Ljava/lang/reflect/Constructor;')
        getFields = JavaMethod('()[Ljava/lang/reflect/Field;')
        getMethods = JavaMethod('()[Ljava/lang/reflect/Method;')
        getName = JavaMethod('()Ljava/lang/String;')

    class Modifier(with_metaclass(JavaClass, JavaObject)):
        __javaclass__ = 'java.lang.reflect.Modifier'
        __javaconstructor__ = JavaMethod('()V')
        isFinal = JavaMethod('(I)Z', static=True)
        isStatic = JavaMethod('(I)Z', static=True)

    class Method(with_metaclass(JavaClass, JavaObject)):
        __javaclass__ = 'java.lang.reflect.Method'
        getModifiers = JavaMethod('()I')
        getName = JavaMethod('()Ljava/lang/String;')
        getParameterTypes = JavaMethod('()[Ljava/lang/Class;')
        getReturnType = JavaMethod('()Ljava/lang/Class;')
        isVarArgs = JavaMethod('()Z')

    class Field(with_metaclass(JavaClass, JavaObject)):
        __javaclass__ = 'java.lang.reflect.Field'
        getModifiers = JavaMethod('()I')
        getName = JavaMethod('()Ljava/lang/String;')
        getType = JavaMethod('()Ljava/lang/Class;')

    class Constructor(with_metaclass(JavaClass, JavaObject)):
        __javaclass__ = 'java.lang.reflect.Constructor'
        getModifiers = JavaMethod('()I')
        getName = JavaMethod('()Ljava/lang/String;')
        getParameterTypes = JavaMethod('()[Ljava/lang/Class;')
        isVarArgs = JavaMethod('()Z')

    # The last class defined should match the check at the top of this function.

    classes = [Class, Modifier, Method, Field, Constructor]
    for cls in classes:
        cache_class(cls)

    # Now fill in all the other members.
    for cls in classes:
        cache_class(reflect_class(cls.__name__))


def jclass(clsname):
    """Returns the Java class proxy for the given fully-qualified class name. The name may use
    either '.' or '/' notation. To refer to a nested or inner class, use '$' as the separator,
    e.g. `java.lang.Map$Entry`.

    To create new instances of the class, simply call it like a normal Python class::

        StringBuffer = jclass("java.lang.StringBuffer")
        sb = StringBuffer(1024)
    
    As in Java, static methods and fields can be accessed on either the class or instances of
    the class, while instance methods and fields can only be accessed on instances::

        FIXME give examples of the above

    If a method or field name clashes with a Python reserved word, an underscore is appended,
    e.g. `print` becomes `print_`. The original name is still accessible via `getattr`.

    The Java class hierarchy is not currently reflected in Python, e.g. `issubclass(String,
    Object)` and `isinstance(String("hello"), Object) will both return `False`. This may change
    in the future.

    Link to sections on type conversion and overloading (which should maybe be combined).

        Java objects returned from methods or read from fields are represented as their actual
        run-time type, not the declared type of the method or field. To change this, pass the
        object to the :any:`cast` function.
    """
    clsname = clsname.replace('/', '.')
    cls = jclass_cache.get(clsname)
    if cls:
        return cls

    if clsname.startswith('$Proxy'):
        # The Dalvik VM is not able to give us introspection on these (FindClass returns NULL).
        return jclass("java.lang.Object")

    cls = reflect_class(clsname)
    cache_class(cls)
    return cls


def reflect_class(clsname):
    setup_bootstrap_classes()

    if clsname.startswith("["):
        raise ValueError("Cannot reflect an array type")
    if clsname in java.primitives_by_name:
        raise ValueError("Cannot reflect a primitive type")

    classDict = {"__javaclass__": clsname}
    c = Class(instance=CQPEnv().FindClass(clsname))

    methods = c.getMethods() + c.getConstructors()
    methods_name = [x.getName() for x in methods]
    for index, method in enumerate(methods):
        name = methods_name[index]
        if name in classDict:
            continue

        if methods_name.count(name) == 1:
            method = JavaMethod(method_signature(method),
                                static=Modifier.isStatic(method.getModifiers()),
                                varargs=method.isVarArgs())
        else:
            jms = []
            for index, subname in enumerate(methods_name):
                if subname != name:
                    continue
                method = methods[index]
                jms.append(JavaMethod(method_signature(method),
                                      static=Modifier.isStatic(method.getModifiers()),
                                      varargs=method.isVarArgs()))
            method = JavaMultipleMethod(jms)

        if name == clsname:
            # The constructor's name in java.lang.reflect is the fully-qualified class name,
            # and its name in JNI is "<init>", but neither of those are valid Python
            # identifiers.
            name = "__javaconstructor__"
        classDict[name] = method

    for field in c.getFields():
        modifiers = field.getModifiers()
        classDict[field.getName()] = JavaField(jni_sig(field.getType()),
                                               static=Modifier.isStatic(modifiers),
                                               final=Modifier.isFinal(modifiers))

    return JavaClass(clsname, (JavaObject,), classDict)


def cache_class(cls):
    jclass_cache[cls.__name__] = cls


def method_signature(method):
    if hasattr(method, "getReturnType"):
        return_type = method.getReturnType()
    else:  # Constructor
        return_type = jvoid
    return jni_method_sig(return_type, method.getParameterTypes())