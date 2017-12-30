package com.chaquo.python;

import java.util.*;

public class TestOverload {

    public static class MixedStaticInstance {
        public static String resolve11(Object j) { return "Object"; }
        public String resolve11(String j) { return "String"; }

        public static String resolve10(String s) { return "String"; }
        public String resolve10() { return ""; }

        public static String resolve01() { return ""; }
        public String resolve01(String s) { return "String"; }

        public static String toString(Integer x) { return "Integer"; }
    }


    public static class Parent {
        public Object resolve(Object j) {               // Overridden normally
            return "Parent Object";
        }
        public Object resolve(Integer j) {              // Overridden covariantly
            return "Parent Integer";
        }
        public Object resolve(Object j, String k) {     // Not overridden
            return "Parent Object, String";
        }
    }

    public static class Child extends Parent {
        @Override public Object resolve(Object j) {
            return "Child Object";
        }
        @Override public String resolve(Integer j) {
            return "Child Integer";
        }
        public Object resolve(String j) {
            return "Child String";
        }
        public Object resolve(String j, Object k) {
            return "Child String, Object";
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

        public String resolve_SF(short a) {
            return "short " + a;
        }
        public String resolve_SF(float a) {
            return "float " + a;
        }

        public String resolve_IJ(int a) {
            return "int " + a;
        }
        public String resolve_IJ(long a) {
            return "long " + a;
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

        public String resolve_Short_Long(Short a) {
            return "Short " + a;
        }
        public String resolve_Short_Long(Long a) {
            return "Long " + a;
        }

        public String resolve_Integer_Float(Integer a) {
            return "Integer " + a;
        }
        public String resolve_Integer_Float(Float a) {
            return "Float " + a;
        }

        public String resolve_Float_Double(Float a) {
            return "Float " + a;
        }
        public String resolve_Float_Double(Double a) {
            return "Double " + a;
        }
    }


    public static class TestString {
        public String resolve_C_Character(char a) {
            return "char " + a;
        }
        public String resolve_C_Character(Character a) {
            return "Character " + a;
        }

        public String resolve_C_String(char a) {
            return "char " + a;
        }
        public String resolve_C_String(String a) {
            return "String " + a;
        }

        public String resolve_C_Object(char a) {
            return "char " + a;
        }
        public String resolve_C_Object(Object a) {
            return "Object " + a;
        }

        public String resolve_Character_String(Character a) {
            return "Character " + a;
        }
        public String resolve_Character_String(String a) {
            return "String " + a;
        }

        public String resolve_Character_Object(Character a) {
            return "Character " + a;
        }
        public String resolve_Character_Object(Object a) {
            return "Object " + a;
        }
    }


    public static class TestArray {
        public String resolve_ZB(boolean[] a) {
            return "boolean[] " + Arrays.toString(a);
        }
        public String resolve_ZB(byte[] a) {
            return "byte[] " + Arrays.toString(a);
        }

        public String resolve_Object_Number(Object[] a) {
            return "Object[] " + Arrays.toString(a);
        }
        public String resolve_Object_Number(Number[] a) {
            return "Number[] " + Arrays.toString(a);
        }

        public String resolve_Integer_Long(Integer[] a) {
            return "Integer[] " + Arrays.toString(a);
        }
        public String resolve_Integer_Long(Long[] a) {
            return "Long[] " + Arrays.toString(a);
        }

        public String resolve_Z_Object(boolean[] a) {
            return "boolean[] " + Arrays.toString(a);
        }
        public String resolve_Z_Object(Object a) {
            return "Object " + Arrays.toString((boolean[])a);
        }
    }


    public static class Varargs {
        public String resolve_empty_single_I() {
            return "";
        }
        public String resolve_empty_single_I(int a) {
            return "int " + a;
        }
        public String resolve_empty_single_I(int... a) {
            return "int... " + Arrays.toString(a);
        }

        public String resolve_ID(int a) {
            return "int " + a;
        }
        public String resolve_ID(double a) {
            return "double " + a;
        }
        public String resolve_ID(int... a) {
            return "int... " + Arrays.toString(a);
        }
        public String resolve_ID(double... a) {
            return "double... " + Arrays.toString(a);
        }

        public String resolve_I_Long(int... a) {
            return "int... " + Arrays.toString(a);
        }
        public String resolve_I_Long(Long... a) {
            return "Long... " + Arrays.toString(a);
        }

        public String resolve_Number_Long(Number... a) {
            return "Number... " + Arrays.toString(a);
        }
        public String resolve_Number_Long(Long... a) {
            return "Long... " + Arrays.toString(a);
        }
    }

}
