package com.chaquo.python;

/** An exception propagating from Python to Java. If the exception was of a Java exception type,
 * the original exception is stored as the cause of the PyException. `getStackTrace` will return
 * a combined Python and Java stack trace, with Python frames indicated by a top-level package name
 * of "&lt;python&gt;"*/
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
