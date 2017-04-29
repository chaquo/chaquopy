package com.chaquo.python;

// Has to be unchecked because it can be thrown by PyObject methods inherited from Map.
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
