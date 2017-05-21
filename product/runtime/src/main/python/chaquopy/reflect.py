from __future__ import absolute_import, division, print_function
from six import with_metaclass

from .chaquopy import (JavaObject, JavaClass, JavaMethod, JavaField, JavaMultipleMethod,
                       find_javaclass)
from .signatures import *

__all__ = ['autoclass']


autoclass_cache = {}


# This isn't done during module initialization because we don't have a JVM yet, and we don't
# want to automatically start one because we might already be in a Java process.
def setup_bootstrap_classes():
    if "Constructor" in globals():  # Last class to be defined
        return

    global Class, Object, Modifier, Method, Field, Constructor

    # Generated with runtime/make_proxy.py
    # TODO this still omits the base class methods of AccessibleObject.

    class Class(with_metaclass(JavaClass, JavaObject)):
        __javaclass__ = 'java.lang.Class'
        asSubclass = JavaMethod('(Ljava/lang/Class;)Ljava/lang/Class;')
        cast = JavaMethod('(Ljava/lang/Object;)Ljava/lang/Object;')
        desiredAssertionStatus = JavaMethod('()Z')
        equals = JavaMethod('(Ljava/lang/Object;)Z')
        forName = JavaMultipleMethod([
            JavaMethod('(Ljava/lang/String;)Ljava/lang/Class;', static=True),
            JavaMethod('(Ljava/lang/String;ZLjava/lang/ClassLoader;)Ljava/lang/Class;', static=True)])
        getAnnotatedInterfaces = JavaMethod('()[Ljava/lang/reflect/AnnotatedType;')
        getAnnotatedSuperclass = JavaMethod('()Ljava/lang/reflect/AnnotatedType;')
        getAnnotation = JavaMethod('(Ljava/lang/Class;)Ljava/lang/annotation/Annotation;')
        getAnnotations = JavaMethod('()[Ljava/lang/annotation/Annotation;')
        getAnnotationsByType = JavaMethod('(Ljava/lang/Class;)[Ljava/lang/annotation/Annotation;')
        getCanonicalName = JavaMethod('()Ljava/lang/String;')
        getClass = JavaMethod('()Ljava/lang/Class;')
        getClassLoader = JavaMethod('()Ljava/lang/ClassLoader;')
        getClasses = JavaMethod('()[Ljava/lang/Class;')
        getComponentType = JavaMethod('()Ljava/lang/Class;')
        getConstructor = JavaMethod('([Ljava/lang/Class;)Ljava/lang/reflect/Constructor;', varargs=True)
        getConstructors = JavaMethod('()[Ljava/lang/reflect/Constructor;')
        getDeclaredAnnotation = JavaMethod('(Ljava/lang/Class;)Ljava/lang/annotation/Annotation;')
        getDeclaredAnnotations = JavaMethod('()[Ljava/lang/annotation/Annotation;')
        getDeclaredAnnotationsByType = JavaMethod('(Ljava/lang/Class;)[Ljava/lang/annotation/Annotation;')
        getDeclaredClasses = JavaMethod('()[Ljava/lang/Class;')
        getDeclaredConstructor = JavaMethod('([Ljava/lang/Class;)Ljava/lang/reflect/Constructor;', varargs=True)
        getDeclaredConstructors = JavaMethod('()[Ljava/lang/reflect/Constructor;')
        getDeclaredField = JavaMethod('(Ljava/lang/String;)Ljava/lang/reflect/Field;')
        getDeclaredFields = JavaMethod('()[Ljava/lang/reflect/Field;')
        getDeclaredMethod = JavaMethod('(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;', varargs=True)
        getDeclaredMethods = JavaMethod('()[Ljava/lang/reflect/Method;')
        getDeclaringClass = JavaMethod('()Ljava/lang/Class;')
        getEnclosingClass = JavaMethod('()Ljava/lang/Class;')
        getEnclosingConstructor = JavaMethod('()Ljava/lang/reflect/Constructor;')
        getEnclosingMethod = JavaMethod('()Ljava/lang/reflect/Method;')
        getEnumConstants = JavaMethod('()[Ljava/lang/Object;')
        getField = JavaMethod('(Ljava/lang/String;)Ljava/lang/reflect/Field;')
        getFields = JavaMethod('()[Ljava/lang/reflect/Field;')
        getGenericInterfaces = JavaMethod('()[Ljava/lang/reflect/Type;')
        getGenericSuperclass = JavaMethod('()Ljava/lang/reflect/Type;')
        getInterfaces = JavaMethod('()[Ljava/lang/Class;')
        getMethod = JavaMethod('(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;', varargs=True)
        getMethods = JavaMethod('()[Ljava/lang/reflect/Method;')
        getModifiers = JavaMethod('()I')
        getName = JavaMethod('()Ljava/lang/String;')
        getPackage = JavaMethod('()Ljava/lang/Package;')
        getProtectionDomain = JavaMethod('()Ljava/security/ProtectionDomain;')
        getResource = JavaMethod('(Ljava/lang/String;)Ljava/net/URL;')
        getResourceAsStream = JavaMethod('(Ljava/lang/String;)Ljava/io/InputStream;')
        getSigners = JavaMethod('()[Ljava/lang/Object;')
        getSimpleName = JavaMethod('()Ljava/lang/String;')
        getSuperclass = JavaMethod('()Ljava/lang/Class;')
        getTypeName = JavaMethod('()Ljava/lang/String;')
        getTypeParameters = JavaMethod('()[Ljava/lang/reflect/TypeVariable;')
        hashCode = JavaMethod('()I')
        isAnnotation = JavaMethod('()Z')
        isAnnotationPresent = JavaMethod('(Ljava/lang/Class;)Z')
        isAnonymousClass = JavaMethod('()Z')
        isArray = JavaMethod('()Z')
        isAssignableFrom = JavaMethod('(Ljava/lang/Class;)Z')
        isEnum = JavaMethod('()Z')
        isInstance = JavaMethod('(Ljava/lang/Object;)Z')
        isInterface = JavaMethod('()Z')
        isLocalClass = JavaMethod('()Z')
        isMemberClass = JavaMethod('()Z')
        isPrimitive = JavaMethod('()Z')
        isSynthetic = JavaMethod('()Z')
        newInstance = JavaMethod('()Ljava/lang/Object;')
        notify = JavaMethod('()V')
        notifyAll = JavaMethod('()V')
        toGenericString = JavaMethod('()Ljava/lang/String;')
        toString = JavaMethod('()Ljava/lang/String;')
        wait = JavaMultipleMethod([
            JavaMethod('(J)V'),
            JavaMethod('(JI)V'),
            JavaMethod('()V')])

    class Object(with_metaclass(JavaClass, JavaObject)):
        __javaclass__ = 'java.lang.Object'
        __javaconstructor__ = JavaMethod('()V')
        equals = JavaMethod('(Ljava/lang/Object;)Z')
        getClass = JavaMethod('()Ljava/lang/Class;')
        hashCode = JavaMethod('()I')
        notify = JavaMethod('()V')
        notifyAll = JavaMethod('()V')
        toString = JavaMethod('()Ljava/lang/String;')
        wait = JavaMultipleMethod([
            JavaMethod('(J)V'),
            JavaMethod('(JI)V'),
            JavaMethod('()V')])

    class Modifier(with_metaclass(JavaClass, JavaObject)):
        __javaclass__ = 'java.lang.reflect.Modifier'
        __javaconstructor__ = JavaMethod('()V')
        classModifiers = JavaMethod('()I', static=True)
        constructorModifiers = JavaMethod('()I', static=True)
        equals = JavaMethod('(Ljava/lang/Object;)Z')
        fieldModifiers = JavaMethod('()I', static=True)
        getClass = JavaMethod('()Ljava/lang/Class;')
        hashCode = JavaMethod('()I')
        interfaceModifiers = JavaMethod('()I', static=True)
        isAbstract = JavaMethod('(I)Z', static=True)
        isFinal = JavaMethod('(I)Z', static=True)
        isInterface = JavaMethod('(I)Z', static=True)
        isNative = JavaMethod('(I)Z', static=True)
        isPrivate = JavaMethod('(I)Z', static=True)
        isProtected = JavaMethod('(I)Z', static=True)
        isPublic = JavaMethod('(I)Z', static=True)
        isStatic = JavaMethod('(I)Z', static=True)
        isStrict = JavaMethod('(I)Z', static=True)
        isSynchronized = JavaMethod('(I)Z', static=True)
        isTransient = JavaMethod('(I)Z', static=True)
        isVolatile = JavaMethod('(I)Z', static=True)
        methodModifiers = JavaMethod('()I', static=True)
        notify = JavaMethod('()V')
        notifyAll = JavaMethod('()V')
        parameterModifiers = JavaMethod('()I', static=True)
        toString = JavaMethod('(I)Ljava/lang/String;', static=True)
        wait = JavaMultipleMethod([
            JavaMethod('(J)V'),
            JavaMethod('(JI)V'),
            JavaMethod('()V')])

    class Method(with_metaclass(JavaClass, JavaObject)):
        __javaclass__ = 'java.lang.reflect.Method'
        equals = JavaMethod('(Ljava/lang/Object;)Z')
        getAnnotatedReturnType = JavaMethod('()Ljava/lang/reflect/AnnotatedType;')
        getAnnotation = JavaMethod('(Ljava/lang/Class;)Ljava/lang/annotation/Annotation;')
        getClass = JavaMethod('()Ljava/lang/Class;')
        getDeclaredAnnotations = JavaMethod('()[Ljava/lang/annotation/Annotation;')
        getDeclaringClass = JavaMethod('()Ljava/lang/Class;')
        getDefaultValue = JavaMethod('()Ljava/lang/Object;')
        getExceptionTypes = JavaMethod('()[Ljava/lang/Class;')
        getGenericExceptionTypes = JavaMethod('()[Ljava/lang/reflect/Type;')
        getGenericParameterTypes = JavaMethod('()[Ljava/lang/reflect/Type;')
        getGenericReturnType = JavaMethod('()Ljava/lang/reflect/Type;')
        getModifiers = JavaMethod('()I')
        getName = JavaMethod('()Ljava/lang/String;')
        getParameterAnnotations = JavaMethod('()[[Ljava/lang/annotation/Annotation;')
        getParameterCount = JavaMethod('()I')
        getParameterTypes = JavaMethod('()[Ljava/lang/Class;')
        getReturnType = JavaMethod('()Ljava/lang/Class;')
        getTypeParameters = JavaMethod('()[Ljava/lang/reflect/TypeVariable;')
        hashCode = JavaMethod('()I')
        invoke = JavaMethod('(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;', varargs=True)
        isBridge = JavaMethod('()Z')
        isDefault = JavaMethod('()Z')
        isSynthetic = JavaMethod('()Z')
        isVarArgs = JavaMethod('()Z')
        notify = JavaMethod('()V')
        notifyAll = JavaMethod('()V')
        toGenericString = JavaMethod('()Ljava/lang/String;')
        toString = JavaMethod('()Ljava/lang/String;')
        wait = JavaMultipleMethod([
            JavaMethod('(J)V'),
            JavaMethod('(JI)V'),
            JavaMethod('()V')])

    class Field(with_metaclass(JavaClass, JavaObject)):
        __javaclass__ = 'java.lang.reflect.Field'
        equals = JavaMethod('(Ljava/lang/Object;)Z')
        get = JavaMethod('(Ljava/lang/Object;)Ljava/lang/Object;')
        getAnnotatedType = JavaMethod('()Ljava/lang/reflect/AnnotatedType;')
        getAnnotation = JavaMethod('(Ljava/lang/Class;)Ljava/lang/annotation/Annotation;')
        getAnnotationsByType = JavaMethod('(Ljava/lang/Class;)[Ljava/lang/annotation/Annotation;')
        getBoolean = JavaMethod('(Ljava/lang/Object;)Z')
        getByte = JavaMethod('(Ljava/lang/Object;)B')
        getChar = JavaMethod('(Ljava/lang/Object;)C')
        getClass = JavaMethod('()Ljava/lang/Class;')
        getDeclaredAnnotations = JavaMethod('()[Ljava/lang/annotation/Annotation;')
        getDeclaringClass = JavaMethod('()Ljava/lang/Class;')
        getDouble = JavaMethod('(Ljava/lang/Object;)D')
        getFloat = JavaMethod('(Ljava/lang/Object;)F')
        getGenericType = JavaMethod('()Ljava/lang/reflect/Type;')
        getInt = JavaMethod('(Ljava/lang/Object;)I')
        getLong = JavaMethod('(Ljava/lang/Object;)J')
        getModifiers = JavaMethod('()I')
        getName = JavaMethod('()Ljava/lang/String;')
        getShort = JavaMethod('(Ljava/lang/Object;)S')
        getType = JavaMethod('()Ljava/lang/Class;')
        hashCode = JavaMethod('()I')
        isEnumConstant = JavaMethod('()Z')
        isSynthetic = JavaMethod('()Z')
        notify = JavaMethod('()V')
        notifyAll = JavaMethod('()V')
        set = JavaMethod('(Ljava/lang/Object;Ljava/lang/Object;)V')
        setBoolean = JavaMethod('(Ljava/lang/Object;Z)V')
        setByte = JavaMethod('(Ljava/lang/Object;B)V')
        setChar = JavaMethod('(Ljava/lang/Object;C)V')
        setDouble = JavaMethod('(Ljava/lang/Object;D)V')
        setFloat = JavaMethod('(Ljava/lang/Object;F)V')
        setInt = JavaMethod('(Ljava/lang/Object;I)V')
        setLong = JavaMethod('(Ljava/lang/Object;J)V')
        setShort = JavaMethod('(Ljava/lang/Object;S)V')
        toGenericString = JavaMethod('()Ljava/lang/String;')
        toString = JavaMethod('()Ljava/lang/String;')
        wait = JavaMultipleMethod([
            JavaMethod('(J)V'),
            JavaMethod('(JI)V'),
            JavaMethod('()V')])

    class Constructor(with_metaclass(JavaClass, JavaObject)):
        __javaclass__ = 'java.lang.reflect.Constructor'
        equals = JavaMethod('(Ljava/lang/Object;)Z')
        getAnnotatedReceiverType = JavaMethod('()Ljava/lang/reflect/AnnotatedType;')
        getAnnotatedReturnType = JavaMethod('()Ljava/lang/reflect/AnnotatedType;')
        getAnnotation = JavaMethod('(Ljava/lang/Class;)Ljava/lang/annotation/Annotation;')
        getClass = JavaMethod('()Ljava/lang/Class;')
        getDeclaredAnnotations = JavaMethod('()[Ljava/lang/annotation/Annotation;')
        getDeclaringClass = JavaMethod('()Ljava/lang/Class;')
        getExceptionTypes = JavaMethod('()[Ljava/lang/Class;')
        getGenericExceptionTypes = JavaMethod('()[Ljava/lang/reflect/Type;')
        getGenericParameterTypes = JavaMethod('()[Ljava/lang/reflect/Type;')
        getModifiers = JavaMethod('()I')
        getName = JavaMethod('()Ljava/lang/String;')
        getParameterAnnotations = JavaMethod('()[[Ljava/lang/annotation/Annotation;')
        getParameterCount = JavaMethod('()I')
        getParameterTypes = JavaMethod('()[Ljava/lang/Class;')
        getTypeParameters = JavaMethod('()[Ljava/lang/reflect/TypeVariable;')
        hashCode = JavaMethod('()I')
        isSynthetic = JavaMethod('()Z')
        isVarArgs = JavaMethod('()Z')
        newInstance = JavaMethod('([Ljava/lang/Object;)Ljava/lang/Object;', varargs=True)
        notify = JavaMethod('()V')
        notifyAll = JavaMethod('()V')
        toGenericString = JavaMethod('()Ljava/lang/String;')
        toString = JavaMethod('()Ljava/lang/String;')
        wait = JavaMultipleMethod([
            JavaMethod('(J)V'),
            JavaMethod('(JI)V'),
            JavaMethod('()V')])

    # The last class defined should match the check at the top of this function.

    for cls in [Class, Object, Modifier, Method, Field, Constructor]:
        cache_class(cls)


def lower_name(s):
    return s[:1].lower() + s[1:] if s else ''


def bean_getter(s):
    return (s.startswith('get') and len(s) > 3 and s[3].isupper()) or (s.startswith('is') and len(s) > 2 and s[2].isupper())


def autoclass(clsname):
    """Returns the Java class proxy for the given fully-qualified class name. The name may use
    either '.' or '/' notation. To refer to a nested or inner class, use '$' as the separator,
    e.g. `java.lang.Map$Entry`.

    To create new instances of the class, simply call it like a normal Python class::

        StringBuffer = autoclass("java.lang.StringBuffer")
        sb = StringBuffer(1024)
    
    As in Java, static methods and fields can be accessed on either the class or instances of
    the class, while instance methods and fields can only be accessed on instances::

        FIXME give examples of the above

    The Java class hierarchy is not currently reflected in Python, e.g. `issubclass(String,
    Object)` and `isinstance(String("hello"), Object) will both return `False`. This may change
    in the future.

    Link to sections on type conversion and overloading (which should maybe be combined).

        Java objects returned from methods or read from fields are represented as their actual
        run-time type, not the declared type of the method or field. To change this, pass the
        object to the :any:`cast` function.
    """
    clsname = clsname.replace('/', '.')
    cls = autoclass_cache.get(clsname)
    if cls:
        return cls

    if clsname.startswith('$Proxy'):
        # The Dalvik VM is not able to give us introspection on these (FindClass returns NULL).
        return Object

    classDict = {"__javaclass__": clsname}
    c = find_javaclass(clsname)
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
            # TODO disabled until tested (#5153), and should also generate a setter, AND should
            # be moved to the metaclass so it also takes effect on bootstrap classes.
            #
            # if name != 'getClass' and bean_getter(name) and len(method.getParameterTypes()) == 0:
            #     classDict[lower_name(name[3:])] = \
            #         (lambda n: property(lambda self: getattr(self, n)()))(name)
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

    cls = JavaClass(clsname, (JavaObject,), classDict)
    cache_class(cls)
    return cls


def cache_class(cls):
    autoclass_cache[cls.__javaclass__.replace("/", ".")] = cls


def method_signature(method):
    if method.getClass().getName() == "java.lang.reflect.Constructor":
        return_type = jvoid
    else:
        return_type = method.getReturnType()
    return jni_method_sig(return_type, method.getParameterTypes())
