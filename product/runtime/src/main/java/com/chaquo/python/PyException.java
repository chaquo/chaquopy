package com.chaquo.python;

/** <p>An exception thrown from Python to Java.</p>
 *
 * <p>If the exception originated from Java, the original exception object can be retrieved by
 * calling {@link #getCause getCause}.</p>
 *
 * <p>{@link #getStackTrace getStackTrace} will return a combined Python and Java stack trace,
 * where Python frames will have a package name starting "&lt;python&gt;".</p> */

// Has to be unchecked because it can be thrown by virtually all the methods in this package,
// including those inherited from Map which we can't add "throws" declarations to.

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
