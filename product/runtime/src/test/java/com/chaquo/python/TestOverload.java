package com.chaquo.python;

public class TestOverload {

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
            return "boolean " + a;
        }
        public String resolve(byte a) {
            return "byte " + a;
        }
        public String resolve(short a) {
            return "short " + a;
        }
        public String resolve(int a) {
            return "int " + a;
        }
        public String resolve(long a) {
            return "long " + a;
        }
        public String resolve(float a) {
            return "float " + a;
        }
        public String resolve(double a) {
            return "double " + a;
        }
        public String resolve(char a) {
            return "char " + a;
        }
        public String resolve(String a) {
            return "String " + a;
        }

        public String resolve_SF(short a) {
            return "short " + a;
        }
        public String resolve_SF(float a) {
            return "float " + a;
        }

        public String resolve_BIF(byte a) {
            return "byte " + a;
        }
        public String resolve_BIF(int a) {
            return "int " + a;
        }
        public String resolve_BIF(float a) {
            return "float " + a;
        }

        public String resolve_FD(float a) {
            return "float " + a;
        }
        public String resolve_FD(double a) {
            return "double " + a;
        }
    }


    public static class Boxing {
        public String resolve_Z_Boolean(boolean a) {
            return "boolean " + a;
        }
        public String resolve_Z_Boolean(Boolean a) {
            return "Boolean " + a;
        }

        public String resolve_Z_Object(boolean a) {
            return "boolean " + a;
        }
        public String resolve_Z_Object(Object a) {
            return "Object " + a;
        }

        public String resolve_S_Long(short a) {
            return "short " + a;
        }
        public String resolve_S_Long(Long a) {
            return "Long " + a;
        }

        public String resolve_Short_L(Short a) {
            return "Short " + a;
        }
        public String resolve_Short_L(long a) {
            return "long " + a;
        }

        public String resolve_Integer_Long(Integer a) {
            return "Integer " + a;
        }
        public String resolve_Integer_Long(Long a) {
            return "Long " + a;
        }

    }


    public static class Arrays {
        // FIXME probably move everything from TestBasics into here
    }


    public static class Varargs {
        // FIXME probably move everything from TestBasics into here
        // Also include interaction with arrays
    }

}
