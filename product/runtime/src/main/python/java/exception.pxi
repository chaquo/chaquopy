def Throwable_str(self):
    try:
        sw = jclass("java.io.StringWriter")()
        pw = jclass("java.io.PrintWriter")(sw)
        self.printStackTrace(pw)
        pw.close()
        result = sw.toString().strip()
        prefix = f"{cls_fullname(type(self))}: "
        if result.startswith(prefix):
            result = result[len(prefix):]
    except Exception as e:
        return f"[failed to get traceback: {type(e).__name__}: {e}]"
    else:
        return result

global_class("java.lang.Throwable", cls_dict={"_chaquopy_post_bases": [Exception],
                                              "__str__": Throwable_str})


cdef expect_exception(JNIEnv *j_env, msg):
    """Raises a Java exception if one is pending, otherwise raises a Python Exception with the
    given message.
    """
    check_exception(j_env)
    raise Exception(msg)


cdef jmethodID mid_getMessage = NULL

cdef check_exception(JNIEnv *j_env):
    env = CQPEnv()
    j_exc = env.ExceptionOccurred()
    if not j_exc:
        return
    env.ExceptionClear()

    try:
        exc = j2p(env.j_env, j_exc)
    except Exception as exc2:
        global mid_getMessage
        if not mid_getMessage:
            j_Throwable = env.FindClass("java.lang.Throwable")
            mid_getMessage = env.GetMethodID(j_Throwable, "getMessage", "()Ljava/lang/String;")
        j_message = env.adopt(env.j_env[0].CallObjectMethod(env.j_env, j_exc.obj, mid_getMessage))
        raise Exception(f"{java.sig_to_java(object_sig(env, j_exc))}: "
                        f"{j2p_string(env.j_env, j_message)} "
                        f"[failed to convert: {type(exc2).__name__}: {exc2}]")
    else:
        raise exc
