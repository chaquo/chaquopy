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


# Used in CQPEnv.check_exception.
cdef jmethodID mid_getMessage = NULL
