package com.chaquo.python;

/** See test_overload.py */
public class Overload {

    public static class Basic {
        public String resolve() {
            return "";
        }
        public String resolve(String i) {
            return "String";
        }
        public String resolve(String i, String j) {
            return "String, String";
        }
        public String resolve(String i, String j, int k) {
            return "String, String, int";
        }
        public String resolve(String i, String j, int k, int l) {
            return "String, String, int, int";
        }
        public String resolve(String i, String j, int... integers) {
            return "String, String, int...";
        }
        public String resolve(int... integers) {
            return "int...";
        }
    }


    public static class MixedStaticInstance {
        public static String resolve(Object j) {
            return "Object";
        }
        public String resolve(String j) {
            return "String";
        }
    }


    public static class Parent {
        public String resolve(Object j) {
            return "Object";
        }
        public String resolve(Object j, String k) {
            return "Object, String";
        }
    }

    public static class Child extends Parent {
        public String resolve(String j) {
            return "String";
        }
        public String resolve(Integer j) {
            return "Integer";
        }
        public String resolve(String j, Object k) {
            return "String, Object";
        }
    }


    public static class Primitive {
        public String resolve(boolean a) {
            return "boolean";
        }
        public String resolve(byte a) {
            return "byte";
        }
        public String resolve(short a) {
            return "short";
        }
        public String resolve(int a) {
            return "int";
        }
        public String resolve(long a) {
            return "long";
        }
        public String resolve(float a) {
            return "float";
        }
        public String resolve(double a) {
            return "double";
        }
        public String resolve(char a) {
            return "char";
        }
        public String resolve(String a) {
            return "String";
        }

        public String resolve_float_double(float a) {
            return "float";
        }
        public String resolve_float_double(double a) {
            return "double";
        }
    }


    public static class Arrays {
        // FIXME probably move everything from Basics into here
    }


    public static class Varargs {
        // FIXME probably move everything from Basics into here
        // Also include interaction with arrays
    }


}
