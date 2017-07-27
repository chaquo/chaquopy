# TODO #5169 use proxy for actual exception class
class JavaException(Exception):
    """Raised when an exception arises from Java code. The message contains the Java exception
    class and stack trace.
    """


cdef expect_exception(JNIEnv *j_env, msg):
    """Raises a Java exception if one is pending, otherwise raises a Python Exception with the
    given message.
    """
    check_exception(j_env)
    raise Exception(msg)


# TODO #5167 is this thread-safe?
processing_exception = False

cdef check_exception(JNIEnv *j_env):
    env = CQPEnv()
    j_exc = env.ExceptionOccurred()
    if not j_exc:
        return
    env.ExceptionClear()

    try:
        global processing_exception
        if processing_exception:
            raise JavaException("Another exception occurred while getting exception details")
        processing_exception = True

        exc = j2p(env.j_env, j_exc)
        PrintWriter = java.jclass("java.io.PrintWriter")
        StringWriter = java.jclass("java.io.StringWriter")
        sw = StringWriter()
        pw = PrintWriter(sw)
        exc.printStackTrace(pw)
        pw.close()
        raise JavaException(sw.toString())

    finally:
        processing_exception = False


cdef jmethodID mid_getName = NULL

# To avoid infinite recursion, this function must not use anything which could call
# lookup_java_object_name itself, including any jclass proxy methods.
cdef lookup_java_object_name(JNIEnv *j_env, jobject j_obj):
    """Returns the fully-qualified class name of the given object, in the same format as
    Class.getName().
    * Array types are returned in JNI format (e.g. "[Ljava/lang/Object;" or "[I".
    * Other types are returned in Java format (e.g. "java.lang.Object"
    """
    j_cls = LocalRef.adopt(j_env, j_env[0].GetObjectClass(j_env, j_obj))

    global mid_getName
    if not mid_getName:
        j_Class = LocalRef.adopt(j_env, j_env[0].GetObjectClass(j_env, j_cls.obj))
        mid_getName = j_env[0].GetMethodID(j_env, j_Class.obj, 'getName', '()Ljava/lang/String;')
        if not mid_getName:
            j_env[0].ExceptionClear(j_env)
            raise Exception("GetMethodID failed")

    j_name = LocalRef.adopt(j_env, j_env[0].CallObjectMethod(j_env, j_cls.obj, mid_getName))
    if not j_name:
        j_env[0].ExceptionClear(j_env)
        raise Exception("getName failed")
    return j2p_string(j_env, j_name.obj)
