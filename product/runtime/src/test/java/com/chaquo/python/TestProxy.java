package com.chaquo.python;

public class TestProxy {

    public static String runResult;
    public static String run(Runnable r) {
        runResult = null;
        r.run();
        return runResult;
    }


    public interface Adder {
        int add(int x);
    }

    public static Adder adder;

    public static int add(Adder adder, int x) {
        return adder.add(x);
    }

    public static String toString(Adder adder) {
        return adder.toString();
    }

}
