package com.chaquo.python;

import static org.junit.Assert.*;


@SuppressWarnings("unused")
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


    public interface Interface1 {}
    public interface Interface1a extends Interface1 {}
    public interface Interface2 {}

    public interface Order_1_2 extends Interface1, Interface2 {}
    public interface Order_2_1 extends Interface2, Interface1 {}
    public static class Diamond implements Order_1_2, Order_2_1 {}
    public static class DiamondChild extends Parent implements Order_1_2, Order_2_1 {}

    public interface Order_1_1a extends Interface1, Interface1a {}
    public interface Order_1a_1 extends Interface1a, Interface1 {}
    public interface Order_1_2_1a extends Interface1, Interface2, Interface1a {}
    public interface Order_1a_2_1 extends Interface1a, Interface2, Interface1 {}

    public interface Order_1a_2 extends Interface1a, Interface2 {}
    public interface Order_12_1a2 extends Order_1_2, Order_1a_2 {}


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

    public static class Call {
        
        // java.util.function is not available until API level 24.
        public interface Function<T,R> {
            R apply(T t);
        }
        public interface Supplier<T> {
            T get();
        }

        public static Function<String,String> anon = new Function<String,String>() {
            @Override public String apply(String s) { return "anon " + s; }
        };

        public static Function<String,String> lamb = (String s) -> "lambda " + s;

        public static String staticMethod(String s) { return "static " + s; }
        public static Function<String,String> staticRef = Call::staticMethod;

        public String s;
        public Supplier<String> boundInstanceRef;
        public Call(String s) {
            this.s = "instance " + s;
            this.boundInstanceRef = this::getS;
        }
        public String getS() { return s; }

        public static Function<Call,String> unboundInstanceRef = Call::getS;
        public static Function<String,Call> constructorRef = Call::new;
    }


    public static class CallInterface {
        // No interfaces.
        public static class NoInterfaces {}

        // A non-functional interface.
        public interface INoMethods {}
        public static class NoMethods implements INoMethods {}

        public interface ITwoMethods {
            String a();
            String b();
        }
        public static class TwoMethods implements ITwoMethods {
            public String a() { return "TwoMethods.a"; }
            public String b() { return "TwoMethods.b"; }
        }

        public interface IA1 { String a(); }
        public interface IA2 { String a(); }
        public interface IAint { String a(int x); }
        public interface IB { String b(); }

        // A single functional interface.
        public static class A1 implements IA1 {
            public String a() { return "A1.a"; }
        }
        public static class Aint implements IAint {
            public String a(int x) { return "Aint.a " + x; }
        }

        // Multiple functional interfaces with the same method.
        public static class A1A2 implements IA1, IA2 {
            public String a() { return "A1A2.a"; }
        }

        // Multiple functional interfaces with different method names.
        public static class A1B implements IA1, IB {
            public String a() { return "A1B.a"; }
            public String b() { return "A1B.b"; }
        }

        // Multiple functional interfaces with the same method name but different signatures.
        public static class A1Aint implements IA1, IAint {
            public String a() { return "A1Aint.a"; }
            public String a(int x) { return "A1Aint.a " + x; }
        }

        // Both functional and non-functional interfaces.
        public static class A1TwoMethods implements IA1, ITwoMethods {
            public String a() { return "A1TwoMethods.a"; }
            public String b() { return "A1TwoMethods.b"; }
        }

        // An abstract class which would be functional if it was an interface.
        public static abstract class AbstractC {
            public abstract String c();
        }
        public static class C extends AbstractC {
            public String c() { return "C.c"; }
        }

        // Public Object methods don't stop an interface from being functional, but protected
        // Object methods do.
        public interface IPublicObjectMethod {
            String a();
            String toString();
        }
        public static class PublicObjectMethod implements IPublicObjectMethod {
            public String a() { return "PublicObjectMethod.a"; }
            public String toString() { return "PublicObjectMethod.toString"; }
        }

        public interface IProtectedObjectMethod {
            String a();
            void finalize();
        }
        public static class ProtectedObjectMethod implements IProtectedObjectMethod {
            public String a() { return "ProtectedObjectMethod.a"; }
            public void finalize() {}
        }

        // If an interface declares one method, and a sub-interface adds a second one, then
        // the sub-interface is not functional.
        public interface IAB extends IA1 {
            String b();
        }
        public static class AB implements IAB {
            public String a() { return "AB.a"; }
            public String b() { return "AB.b"; }
        }
    }


    public static class CallInterfaceDefault {
        // If an interface declares two methods, and a sub-interface provides a default
        // implementation of one of them, then the sub-interface is functional.
        public interface IOneMethod extends CallInterface.ITwoMethods {
            default String a() { return "IOneMethod.a"; }
        }
        public static class OneMethod implements IOneMethod {
            public String b() { return "OneMethod.b"; }
        }

        // If an interface declares one method, and a sub-interface provides a default
        // implementation of it while also adding a second method, then both interfaces are
        // functional.
        public interface IABDefault extends CallInterface.IA1 {
            default String a() { return "IABDefault.a"; }
            String b();
        }
        public static class ABDefault implements IABDefault {
            public String b() { return "ABDefault.b"; }
        }
    }
}
