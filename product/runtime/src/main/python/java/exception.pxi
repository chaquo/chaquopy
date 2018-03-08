import traceback


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
        return f"[failed to format Java stack trace: {type(e).__name__}: {e}]"
    else:
        return result

# This .pxi must be included earlier in the .pyx than any global_class declarations for
# Throwable subclasses.
global_class("java.lang.Throwable", cls_dict={"_chaquopy_post_bases": (Exception,),
                                              "__str__": Throwable_str})


cdef jmethodID mid_getMessage = NULL

# To avoid infinite recursion, this function must not use anything which could call check_exception
# itself, including CQPEnv methods.
cdef check_exception(JNIEnv *j_env):
    global Throwable
    env = CQPEnv()
    j_exc = env.ExceptionOccurred()
    if not j_exc:
        return
    env.ExceptionClear()

    try:
        if Throwable is None:
            raise Exception("bootstrap not complete")
        exc = j2p(env.j_env, j_exc)
    except Exception:
        global mid_getMessage
        if not mid_getMessage:
            j_Throwable = env.FindClass("java.lang.Throwable")
            mid_getMessage = env.GetMethodID(j_Throwable, "getMessage", "()Ljava/lang/String;")
        j_message = env.adopt(env.j_env[0].CallObjectMethod(env.j_env, j_exc.obj, mid_getMessage))
        if j_message:
            message = j2p_string(env.j_env, j_message)
        else:
            env.ExceptionClear()
            message = "[Throwable.getMessage failed]"
        raise Exception(f"{sig_to_java(object_sig(env, j_exc))}: "
                        f"{message} [failed to convert: {traceback.format_exc()}]")
    else:
        raise exc
