package com.chaquo.python;

public class TestException {

    public TestException(boolean doThrow) {
        if (doThrow) {
            throw new RuntimeException("hello constructor");
        }
    }

    public static void simple(int depth) {
        if (depth == 0) throw new RuntimeException("hello method");
        else simple(depth -1);
    }

    public static void chain1() {
        try {
            simple(0);
        } catch (RuntimeException e) {
            throw new RuntimeException("1", e);
        }
    }

    public static void chain2() {
        try {
            chain1();
        } catch (RuntimeException e) {
            throw new RuntimeException("2", e);
        }
    }

}
