'''
This module aims to provide a more human-friendly API for
wiring up Java proxy methods.

You can use the signature function to produce JNI method
signautures for methods; passing JavaObject classes
as return or argument types; provided here are annotations
representing Java's primitive and array times.

Methods can return just a standard primitive type:

>>> signature(jint, ())
'()I'

>>> s.signature(jvoid, [jint])
'(I)V'

Or you can use autoclass proxies to specify Java classes
for return types.

>>> String = autoclass("java.lang.String")
>>> signature(String, ())
'()Ljava/lang/String;'

'''

from . import autoclass, java_method, JavaClass

__all__ = ["jni_sig", "signature", "with_signature", "JArray",
           "jboolean", "jbyte", "jchar", "jdouble", "jfloat", "jint", "jlong", "jshort", "jvoid"]


primitives = {}

class _JavaSignaturePrimitive(object):
    def __init__(self, name, spec):
        self._name = name
        self._spec = spec

    def __repr__(self):
        return "Signature for Java %s type" % name

def _MakeSignaturePrimitive(name, spec):
    p = _JavaSignaturePrimitive(name, spec)
    primitives[name] = p
    return p


jboolean = _MakeSignaturePrimitive("boolean", "Z")
jbyte    = _MakeSignaturePrimitive("byte", "B")
jchar    = _MakeSignaturePrimitive("char", "C")
jdouble  = _MakeSignaturePrimitive("double", "D")
jfloat   = _MakeSignaturePrimitive("float", "F")
jint     = _MakeSignaturePrimitive("int", "I")
jlong    = _MakeSignaturePrimitive("long", "J")
jshort   = _MakeSignaturePrimitive("short", "S")
jvoid    = _MakeSignaturePrimitive("void", "V")


def JArray(of_type):
    ''' Signature helper for identifying arrays of a given object or
    primitive type. Accepts the same parameter types as jni_sig().
    '''
    spec = "[" + jni_sig(of_type)
    return _JavaSignaturePrimitive("array", spec)


def with_signature(returns, takes):
    '''Friendlier version of @java_method that takes the same parameters as signature().
    '''
    sig = signature(returns, takes)
    return java_method(sig)


def signature(returns, takes):
    '''Produces a JNI method signature, taking the provided argument types and returning the given
    return type. Accepts the same parameter types as jni_sig(), but argument types must be
    passed as an iterable.
    '''
    out_takes = []
    for arg in takes:
        out_takes.append(jni_sig(arg))

    return "(" + "".join(out_takes) + ")" + jni_sig(returns)


def jni_sig(c):
    ''' Produces a JNI type signature for the given argument, which may be:
    * A JavaClass
    * A java.lang.Class
    * One of the objects jboolean, jbyte, etc. defined by this module
    * A return value of JArray
    '''
    if isinstance(c, JavaClass):
        return "L" + c.__javaclass__.replace(".", "/") + ";"
    if isinstance(c, autoclass("java.lang.Class")):
        name = c.getName()
        primitive = primitives.get(name)
        if primitive:
            return primitive._spec
        else:
            return "L" + name.replace(".", "/") + ";"
    if isinstance(c, _JavaSignaturePrimitive):
        return c._spec
    raise TypeError("Can't produce signature from {} object".format(type(c).__name__))
