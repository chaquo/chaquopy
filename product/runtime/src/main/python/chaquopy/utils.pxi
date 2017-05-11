import six
from cpython.version cimport PY_MAJOR_VERSION

import chaquopy


def cast(destclass, JavaObject obj):
    """Returns a view of the object as the given fully-qualified class name. This can be used to
    restrict the visible methods of an object in order to affect overload resolution.
    """
    return chaquopy.autoclass(destclass)(instance=obj.j_self)


# FIXME this may fail for app classes on Android, which use a child ClassLoader.
def find_javaclass(name):
    """Returns the java.lang.Class proxy object corresponding to the given fully-qualified class
    name. Either '.' or '/' notation may be used. May raise any of the Java exceptions listed
    at https://docs.oracle.com/javase/8/docs/technotes/guides/jni/spec/functions.html#FindClass
    """
    cdef LocalRef jc
    cdef JNIEnv *j_env = get_jnienv()

    # FIXME all other uses of FindClass need to be guarded with expect_exception as well (see
    # note on exceptions in jni.pxd)
    jniname = str_for_c(name.replace('.', '/'))
    jc = LocalRef.adopt(j_env, j_env[0].FindClass(j_env, jniname))
    if not jc:
        expect_exception(j_env, f"FindClass failed for {name}")

    from . import reflect
    reflect.setup_bootstrap_classes()
    return reflect.Class(instance=jc)


cdef str_for_c(s):
     if PY_MAJOR_VERSION < 3:
        if isinstance(s, unicode):
            return s.encode('utf-8')
        else:
            return s
     else:
        return s.encode('utf-8')


def parse_definition(definition):
    BAD_CHARS = ",."  # ',' should be ';' or nothing, and '.' should be '/'
    for c in BAD_CHARS:
        if c in definition:
            raise ValueError(f"Invalid character '{c}' in definition '{definition}'")

    # not a function, just a field
    if definition[0] != '(':
        return definition, None

    # it's a function!
    argdef, ret = definition[1:].split(')')
    args = []

    while len(argdef):
        c = argdef[0]

        # read the array char(s)
        prefix = ''
        while c == '[':
            prefix += c
            argdef = argdef[1:]
            c = argdef[0]

        # native type
        if c in 'ZBCSIJFD':
            args.append(prefix + c)
            argdef = argdef[1:]
            continue

        # java class
        if c == 'L':
            c, argdef = argdef.split(';', 1)
            args.append(prefix + c + ';')
            continue

        raise ValueError(f"Invalid type code '{c}' in definition '{definition}'")

    return ret, tuple(args)


cdef void expect_exception(JNIEnv *j_env, msg) except *:
    """Raises a Java exception if one is pending, otherwise raises a Python Exception with the
    given message.
    """
    check_exception(j_env)
    raise Exception(msg)

cdef void check_exception(JNIEnv *j_env) except *:
    cdef jmethodID toString = NULL
    cdef jmethodID getCause = NULL
    cdef jmethodID getStackTrace = NULL
    cdef jmethodID getMessage = NULL
    cdef jstring e_msg
    cdef jthrowable exc = j_env[0].ExceptionOccurred(j_env)
    cdef jclass cls_object = NULL
    cdef jclass cls_throwable = NULL
    if exc:
        j_env[0].ExceptionClear(j_env)
        cls_object = j_env[0].FindClass(j_env, "java/lang/Object")
        cls_throwable = j_env[0].FindClass(j_env, "java/lang/Throwable")

        toString = j_env[0].GetMethodID(j_env, cls_object, "toString", "()Ljava/lang/String;");
        getMessage = j_env[0].GetMethodID(j_env, cls_throwable, "getMessage", "()Ljava/lang/String;");
        getCause = j_env[0].GetMethodID(j_env, cls_throwable, "getCause", "()Ljava/lang/Throwable;");
        getStackTrace = j_env[0].GetMethodID(j_env, cls_throwable, "getStackTrace", "()[Ljava/lang/StackTraceElement;");

        e_msg = j_env[0].CallObjectMethod(j_env, exc, getMessage);
        pymsg = "" if e_msg == NULL else j2p_string(j_env, e_msg)

        pystack = []
        _append_exception_trace_messages(j_env, pystack, exc, getCause, getStackTrace, toString)

        pyexcclass = lookup_java_object_name(j_env, exc)

        j_env[0].DeleteLocalRef(j_env, cls_object)
        j_env[0].DeleteLocalRef(j_env, cls_throwable)
        if e_msg != NULL:
            j_env[0].DeleteLocalRef(j_env, e_msg)
        j_env[0].DeleteLocalRef(j_env, exc)

        raise JavaException(f'{pyexcclass}: {pymsg}', pyexcclass, pymsg, pystack)


cdef void _append_exception_trace_messages(
    JNIEnv*      j_env,
    list         pystack,
    jthrowable   exc,
    jmethodID    mid_getCause,
    jmethodID    mid_getStackTrace,
    jmethodID    mid_toString):

    # Get the array of StackTraceElements.
    cdef jobjectArray frames = j_env[0].CallObjectMethod(j_env, exc, mid_getStackTrace)
    cdef jsize frames_length = j_env[0].GetArrayLength(j_env, frames)
    cdef jstring msg_obj
    cdef jobject frame
    cdef jthrowable cause

    # Add Throwable.toString() before descending stack trace messages.
    if frames != NULL:
        msg_obj = j_env[0].CallObjectMethod(j_env, exc, mid_toString)
        pystr = None if msg_obj == NULL else j2p_string(j_env, msg_obj)
        # If this is not the top-of-the-trace then this is a cause.
        if len(pystack) > 0:
            pystack.append("Caused by:")
        pystack.append(pystr)
        if msg_obj != NULL:
            j_env[0].DeleteLocalRef(j_env, msg_obj)

    # Append stack trace messages if there are any.
    if frames_length > 0:
        for i in range(frames_length):
            # Get the string returned from the 'toString()' method of the next frame and append it to the error message.
            frame = j_env[0].GetObjectArrayElement(j_env, frames, i)
            msg_obj = j_env[0].CallObjectMethod(j_env, frame, mid_toString)
            pystr = None if msg_obj == NULL else j2p_string(j_env, msg_obj)
            pystack.append(pystr)
            if msg_obj != NULL:
                j_env[0].DeleteLocalRef(j_env, msg_obj)
            j_env[0].DeleteLocalRef(j_env, frame)

    # If 'exc' has a cause then append the stack trace messages from the cause.
    if frames != NULL:
        cause = j_env[0].CallObjectMethod(j_env, exc, mid_getCause)
        if cause != NULL:
            _append_exception_trace_messages(j_env, pystack, cause,
                                             mid_getCause, mid_getStackTrace, mid_toString)
            j_env[0].DeleteLocalRef(j_env, cause)

    j_env[0].DeleteLocalRef(j_env, frames)


cdef lookup_java_object_name(JNIEnv *j_env, jobject j_obj):
    """Returns the fully-qualified class name of the given object, in the same format as
    Class.getName().
    * Array types are returned in JNI format (e.g. "[Ljava/lang/Object;" or "[I".
    * Other types are returned in Java format (e.g. "java.lang.Object"
    """
    # Can't call getClass() or getName() using autoclass because that'll cause a recursive call
    # when getting the returned object type.
    cdef jclass jcls = j_env[0].GetObjectClass(j_env, j_obj)
    cdef jclass jcls2 = j_env[0].GetObjectClass(j_env, jcls)
    cdef jmethodID jmeth = j_env[0].GetMethodID(j_env, jcls2, 'getName', '()Ljava/lang/String;')
    # Can't call check_exception because that'll cause a recursive call when getting the
    # exception type name.
    if jmeth == NULL:
        raise Exception("GetMethodID failed")
    cdef jobject js = j_env[0].CallObjectMethod(j_env, jcls, jmeth)
    if js == NULL:
        raise Exception("getName failed")

    name = j2p_string(j_env, js)
    j_env[0].DeleteLocalRef(j_env, js)
    j_env[0].DeleteLocalRef(j_env, jcls)
    j_env[0].DeleteLocalRef(j_env, jcls2)
    return name


def is_applicable(sign_args, args, *, varargs):
    if len(args) == len(sign_args):
        if len(args) == 0:
            return True
    elif varargs:
        if len(args) < len(sign_args) - 1:
            return False
    else:
        return False

    cdef JNIEnv *env = get_jnienv()
    for index, sign_arg in enumerate(sign_args):
        if varargs and index == len(sign_args) - 1:
            assert sign_arg[0] == "["
            arg = args[index:]
        else:
            arg = args[index]
        if not arg_is_applicable(env, sign_arg, arg):
            return False

    return True


# Must be consistent with populate_args and p2j
cdef arg_is_applicable(JNIEnv *env, r, arg):
    if r == 'Z':
        return isinstance(arg, bool)
    if r in "BSIJ":
        return isinstance(arg, six.integer_types)
    if r == 'C':
        return isinstance(arg, six.string_types) and len(arg) == 1
    if r == 'F' or r == 'D':
        return isinstance(arg, (six.integer_types, float))
    if r[0] in 'L[':
        try:
            p2j(env, r, arg)
            return True
        except TypeError:
            return False
        except RangeError:
            # The value is out of range, but the type matches, so give
            # JavaMultipleMethod.__call__ a positive result so it doesn't cache a different
            # method incorrectly (FIXME test).
            return True

    raise ValueError(f"Invalid signature '{r}'")


def more_specific(JavaMethod jm1, JavaMethod jm2):
    """Returns whether jm1 is more specific than jm2, according to JLS 15.12.2.5. Choosing the Most
    Specific Method
    """
    # FIXME this is a partial implementation to allow some tests to work
    defs1, defs2 = jm1.definition_args, jm2.definition_args
    return (len(defs1) == len(defs2) and
            all([find_javaclass(def2[1:-1]).isAssignableFrom(find_javaclass(def1[1:-1]))
                 for def1, def2 in zip(defs1, defs2)]))

    # FIXME primitive types also have assignability rules (JLS 4.10), but they won't work with
    # find_javaclass, and maybe not with isAssignableFrom either. For example, consider passing
    # an int to Float(), which has constructors taking both (float) and (double).
    #
    # FIXME (int...) is actualy more specific than (double...), but int[] is not more specific
    # than double[]. https://relaxbuddy.com/forum/thread/20288/bug-with-varargs-and-overloading
