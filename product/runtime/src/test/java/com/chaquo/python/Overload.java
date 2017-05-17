package com.chaquo.python;

public class Overload {

    public static String resolve1() {
        return "resolve1()";
    }

    public static String resolve1(String i) {
        return "resolve1(String)";
    }

    public static String resolve1(String i, String j) {
        return "resolve1(String, String)";
    }

    public static String resolve1(String i, String j, int k) {
        return "resolve1(String, String, int)";
    }

    public static String resolve1(String i, String j, int k, int l) {
        return "resolve1(String, String, int, int)";
    }

    public static String resolve1(String i, String j, int... integers) {
        return "resolve1(String, String, int...)";
    }

    public static String resolve1(int... integers) {
        return "resolve1(int...)";
    }


    public static String resolve2(Object j) {
        return "resolve2(Object)";
    }
    public /* instance */ String resolve2(String j) {
        return "resolve2(String)";
    }
}
