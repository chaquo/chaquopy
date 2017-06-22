package com.chaquo.python;

/** An exception originating from Python code. {@link #getMessage getMessage()} will return the
 * Python stack trace. */
// Has to be unchecked because it can be thrown by virtually all the methods in this package,
// including those inherited from Map which we can't add "throws" declarations to.
//
// TODO #5169 make exception PyObject accessible from PyException.
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
