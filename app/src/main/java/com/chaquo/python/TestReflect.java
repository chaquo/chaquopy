package com.chaquo.python;

import static org.junit.Assert.*;


public class TestReflect {

    // See also equivalent Python implementation in pyobjecttest.py.
    public static class DelTrigger {
        private static int TIMEOUT = 1000;
        public static boolean triggered = false;

        @Override
        protected void finalize() throws Throwable {
            triggered = true;
            super.finalize();
        }

        public static void reset() {
            triggered = false;
        }

        public static void assertTriggered(boolean expected) {
            long deadline = System.currentTimeMillis() + TIMEOUT;
            while (System.currentTimeMillis() < deadline) {
                System.gc();
                System.runFinalization();
                try {
                    assertEquals(expected, triggered);
                    return;
                } catch (AssertionError e) {
                    if (!expected) {
                        throw e;
                    }
                }
                try {
                    Thread.sleep(TIMEOUT / 10);
                } catch (InterruptedException e) { /* ignore */ }
            }
            fail("Not triggered after " + TIMEOUT + " ms");
        }
    }

    public interface Interface {
        String iConstant = "Interface constant";
        String iMethod();
    }

    public interface SubInterface extends Interface { }

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

        @Override public String toString() { return "Child object"; }
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

    public static class ParentOuter {
        public static class ChildNested extends ParentOuter {}
    }

    public static class Access {
        private String priv = "private";
        String pack = "package";
        protected String prot = "protected";
        public String publ = "public";

        private String getPriv() { return priv; }
        String getPack() { return pack; }
        protected String getProt() { return prot; }
        public String getPubl() { return publ; }
    }

}
