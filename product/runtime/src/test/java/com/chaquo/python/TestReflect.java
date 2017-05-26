package com.chaquo.python;

public class TestReflect {

    interface I {
        String iConstant = "I constant";
        String iMethod();
    }

    public static class C implements I {
        @Override
        public String iMethod() {
            return iConstant;
        }
    }

}
