package com.chaquo.python;

public class TestReflect {

    public static class DelTrigger {
        public static boolean delTriggered = false;

        @Override
        protected void finalize() throws Throwable {
            delTriggered = true;
            super.finalize();
        }
    }

    public interface Interface {
        String iConstant = "Interface constant";
        String iMethod();
    }

    public static class Parent {
        public static String pStaticField = "Parent static field";
        public String pField = "Parent field";
        public static String pStaticMethod() { return "Parent static method"; }
        public String pMethod() { return "Parent method"; }

        public static String oStaticField = "Non-overridden static field";
        public String oField = "Non-overridden field";
        public static String oStaticMethod() { return "Non-overridden static method"; }
        public String oMethod() { return "Non-overridden method"; }
    }

    public static class Child extends Parent implements Interface {
        @Override public String iMethod() { return "Implemented method"; }

        public static String oStaticField = "Overridden static field";
        public String oField = "Overridden field";
        public static String oStaticMethod() { return "Overridden static method"; }
        @Override public String oMethod() { return "Overridden method"; }
    }

    public enum SimpleEnum {
        GOOD, BAD, UGLY,
    }

    public static abstract class Abstract {}

    public static class NameClash {
        public static String member = "field";
        public static String member() {
            return "method";
        }
    }

}
