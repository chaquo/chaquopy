package com.chaquo.python;

/** An exception propagating from Python to Java.
 *
 * If the exception originated from Java, the original exception object can be retrieved by
 * calling {@link #getCause getCause}.
 *
 * {@link #getStackTrace getStackTrace} will return a combined Python and Java stack trace,
 * with Python frames indicated by a package name starting "&lt;python&gt;". */

// Has to be unchecked because it can be thrown by virtually all the methods in this package,
// including those inherited from Map which we can't add "throws" declarations to.
//
// TODO #5273 make exception PyObject accessible from PyException.

public class PyException extends RuntimeException {
    public PyException() {
    }

    public PyException(String s) {
        super(s);
    }

    public PyException(String s, Throwable throwable) {
        super(s, throwable);
    }

    public PyException(Throwable throwable) {
        super(throwable);
    }
}
