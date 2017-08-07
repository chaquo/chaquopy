package com.chaquo.python;

public class TestProxy {

    public interface Adder {
        int add(int x);
    }

    public static int add(Adder adder, int x) {
        return adder.add(x);
    }

}
