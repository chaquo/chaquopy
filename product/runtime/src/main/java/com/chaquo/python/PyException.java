package com.chaquo.python;

class PyException extends Exception {
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
