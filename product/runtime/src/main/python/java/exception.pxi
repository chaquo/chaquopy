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
