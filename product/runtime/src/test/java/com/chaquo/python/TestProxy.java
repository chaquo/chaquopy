package com.chaquo.python;

import java.io.*;
import java.lang.reflect.*;

public class TestProxy {

    public interface Adder {
        int constant = 123;
        int add(int x);
    }

    public static Adder a1;
    public static Adder a2;


    public static String toString(Adder adder) {
        return adder.toString();
    }


    public interface GetString {
        String getString();
    }


    public interface Args {
        String tooMany(int a);
        String tooFew();

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


    public static Object newProxy() {
        return Proxy.newProxyInstance(TestProxy.class.getClassLoader(),
                                      new Class[] {Runnable.class, Args.class},
                                      new JavaInvocationHandler());
    }

    public static class JavaInvocationHandler implements InvocationHandler {
        @Override
        public Object invoke(Object o, Method method, Object[] objects) throws Throwable {
            switch (method.getName()) {
                case "run":
                    javaRun = true;
                    return null;
                case "tooFew":
                    return "tf";
                case "addDuck":
                    Class type = method.getParameterTypes()[0];
                    if (type == int.class) {
                        return (int) objects[0] + (int) objects[1] + 1;
                    } else if (type == float.class) {
                        return (float) objects[0] + (float) objects[1] + 1;
                    } else if (type == String.class) {
                        return (String) objects[0] + objects[1] + "X";
                    }
            }
            throw new RuntimeException("Not implemented: " + method.getName());
        }
    }

    public static boolean javaRun = false;


    public interface Exceptions {
        void fnf() throws FileNotFoundException;
        int parse(String s);
    }

}
