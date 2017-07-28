# setup_bootstrap_classes will add this as a base class of java.lang.Throwable.
class JavaException(Exception):
    def __init__(*args, **kwargs):
        JavaObject.__init__(*args, **kwargs)

    def __str__(self):
        sw = jclass("java.io.StringWriter")()
        pw = jclass("java.io.PrintWriter")(sw)
        self.printStackTrace(pw)
        pw.close()
        result = sw.toString().strip()
        prefix = type(self).__name__ + ": "
        if result.startswith(prefix):
            result = result[len(prefix):]
        return result


cdef expect_exception(JNIEnv *j_env, msg):
    """Raises a Java exception if one is pending, otherwise raises a Python Exception with the
    given message.
    """
    check_exception(j_env)
    raise Exception(msg)


cdef check_exception(JNIEnv *j_env):
    env = CQPEnv()
    j_exc = env.ExceptionOccurred()
    if not j_exc:
        return
    env.ExceptionClear()
    raise j2p(env.j_env, j_exc)
