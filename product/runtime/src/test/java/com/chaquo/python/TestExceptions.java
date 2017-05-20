package com.chaquo.python;

public class TestExceptions {

    public void methodException(int depth) throws IllegalArgumentException {
        if (depth == 0) throw new IllegalArgumentException("helloworld");
        else methodException(depth -1);
    }

    public void methodExceptionChained() throws IllegalArgumentException {
        try {
            methodException(5);
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("helloworld2", e);
        }
    }

}
