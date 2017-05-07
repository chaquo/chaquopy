import six
from cpython.version cimport PY_MAJOR_VERSION


def cast(destclass, obj):
    cdef JavaObject jc
    cdef JavaObject jobj = obj
    from .reflect import autoclass
    if (PY_MAJOR_VERSION < 3 and isinstance(destclass, basestring)) or \
          (PY_MAJOR_VERSION >=3 and isinstance(destclass, str)):
        jc = autoclass(destclass)(noinstance=True)
    else:
        jc = destclass(noinstance=True)
    jc.instantiate_from(jobj.j_self)
    return jc


def find_javaclass(name):
    """Returns the java.lang.Class proxy object corresponding to the given fully-qualified class
    name. Either '.' or '/' notation may be used. May raise any of the Java exceptions listed
    at https://docs.oracle.com/javase/8/docs/technotes/guides/jni/spec/functions.html#FindClass
    """
    name = str_for_c(name.replace('.', '/'))
    cdef JavaObject cls
    cdef jclass jc
    cdef JNIEnv *j_env = get_jnienv()

    # FIXME all other uses of FindClass need to be guarded with expect_exception as well (see
    # note on exceptions in jni.pxd)
    jc = j_env[0].FindClass(j_env, name)
    if jc == NULL:
        expect_exception(j_env, f"FindClass failed for {name}")

    from . import reflect
    reflect.setup_bootstrap_classes()
    cls = reflect.Class(noinstance=True)
    cls.instantiate_from(GlobalRef.create(j_env, jc))
    j_env[0].DeleteLocalRef(j_env, jc)
    return cls


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
        pymsg = "" if e_msg == NULL else convert_jobject_to_python(j_env, <bytes> 'Ljava/lang/String;', e_msg)

        pystack = []
        _append_exception_trace_messages(j_env, pystack, exc, getCause, getStackTrace, toString)

        pyexcclass = lookup_java_object_name(j_env, exc).replace('/', '.')

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
        pystr = None if msg_obj == NULL else convert_jobject_to_python(j_env, <bytes> 'Ljava/lang/String;', msg_obj)
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
            pystr = None if msg_obj == NULL else convert_jobject_to_python(j_env, <bytes> 'Ljava/lang/String;', msg_obj)
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
    cdef jclass jcls = j_env[0].GetObjectClass(j_env, j_obj)
    cdef jclass jcls2 = j_env[0].GetObjectClass(j_env, jcls)
    cdef jmethodID jmeth = j_env[0].GetMethodID(j_env, jcls2, 'getName', '()Ljava/lang/String;')
    cdef jobject js = j_env[0].CallObjectMethod(j_env, jcls, jmeth)
    name = convert_jobject_to_python(j_env, 'Ljava/lang/String;', js)
    j_env[0].DeleteLocalRef(j_env, js)
    j_env[0].DeleteLocalRef(j_env, jcls)
    j_env[0].DeleteLocalRef(j_env, jcls2)
    return name.replace('.', '/')


def is_applicable(sign_args, args, *, varargs):
    if len(args) == len(sign_args):
        if len(args) == 0:
            return True
    elif varargs:
        if len(args) < len(sign_args) - 1:
            return False
    else:
        return False

    for index, sign_arg in enumerate(sign_args):
        if varargs and index == len(sign_args) - 1:
            assert sign_arg[0] == "["
            arg = args[index:]
        else:
            arg = args[index]
        if not arg_is_applicable(sign_arg, arg):
            return False
    return True


def arg_is_applicable(r, arg):
    if r == 'Z':
        return isinstance(arg, bool)
    if r in "BSIJ":
        return isinstance(arg, six.integer_types)
    if r == 'C':
        return isinstance(arg, six.string_types) and len(arg) == 1
    if r == 'F' or r == 'D':
        return isinstance(arg, (six.integer_types, float))

    if r[0] == 'L':
        r = r[1:-1]
        r_klass = find_javaclass(r)

        if arg is None:
            return True
        if isinstance(arg, six.string_types):
            return r_klass.isAssignableFrom(find_javaclass("java.lang.String"))
        if isinstance(arg, JavaClass):
            return r_klass.isAssignableFrom(find_javaclass("java.lang.Class"))
        if isinstance(arg, JavaObject):
            return r_klass.isAssignableFrom(find_javaclass(arg.__javaclass__))
        if isinstance(arg, PythonJavaClass):
            return any([r_klass.isAssignableFrom(find_javaclass(i))
                       for i in arg.__javainterfaces__])
        # FIXME also accept primitive types and perform auto-boxing
        return False

    if r[0] == '[':
        if arg is None:
            return True
        if isinstance(arg, (list, tuple)):
            return is_applicable([r[1:]] * len(arg), arg, varargs=False)
        if isinstance(arg, bytearray) and r == '[B':
            return True
        return False

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

    # FIXME (int...) is actualy more specific than (double...), but int[] is not more specific
    # than double[]. https://relaxbuddy.com/forum/thread/20288/bug-with-varargs-and-overloading
