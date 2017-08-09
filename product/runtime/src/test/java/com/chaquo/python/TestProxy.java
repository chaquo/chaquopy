package com.chaquo.python;

public class TestProxy {

    public interface Adder {
        int constant = 123;
        int add(int x);
    }

    public static Adder a;


    public static String toString(Adder adder) {
        return adder.toString();
    }


    public interface Args {
        void tooMany(int a);
        void tooFew();

        int addDuck(int a, int b);
        float addDuck(float a, float b);
        String addDuck(String a, String b);

        String optional();
        String optional(String a);

        String star();
        String star(String a);
        String star(String a, String b);

        String varargs(String delim, String... args);
    }

}
