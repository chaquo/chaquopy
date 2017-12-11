package com.chaquo.java;

import com.chaquo.python.*;
import java.io.*;
import java.lang.reflect.*;
import org.junit.*;
import org.junit.rules.*;
import org.junit.runners.*;
import chaquopy.test.static_proxy.basic.*;
import chaquopy.test.static_proxy.header.*;
import chaquopy.test.static_proxy.method.*;

import static org.junit.Assert.*;
import static org.hamcrest.CoreMatchers.isA;
import static org.hamcrest.CoreMatchers.equalTo;
import static org.junit.internal.matchers.ThrowableMessageMatcher.hasMessage;


@FixMethodOrder(MethodSorters.NAME_ASCENDING)
public class StaticProxyTest {
    @Rule
    public ExpectedException thrown = ExpectedException.none();

    @Test
    public void basic() {
        BasicAdder a1 = new BasicAdder(1);
        BasicAdder a2 = new BasicAdder(2);
        assertEquals(6, a1.add(5));
        assertEquals(7, a2.add(5));
    }

    @Test
    public void toFromJava() {
        Python py = Python.getInstance();
        PyObject BA = py.getModule("chaquopy.test.static_proxy.basic").get("BasicAdder");
        PyObject ba_po = BA.call(42);
        BasicAdder ba = ba_po.toJava(BasicAdder.class);
        assertEquals(45, ba.add(3));
        assertSame(ba_po, PyObject.fromJava(ba));
    }

    @Test
    public void otherPackage() {
        other.pkg.OtherPackage op = new other.pkg.OtherPackage();
        assertEquals("world", op.hello());
    }

    public static class ClassA {}
    public interface IntA {}
    public interface IntB {}

    @SuppressWarnings("ConstantConditions")
    @Test
    public void bases() {
        assertTrue(new Ca() instanceof ClassA);
        assertTrue(new Ia() instanceof IntA);
        assertTrue(new IaIb() instanceof IntA);
        assertTrue(new IaIb() instanceof IntB);
        assertTrue(new CaIa() instanceof ClassA);
        assertTrue(new CaIa() instanceof IntA);
        assertTrue(new CaIaIb() instanceof ClassA);
        assertTrue(new CaIaIb() instanceof IntA);
        assertTrue(new CaIaIb() instanceof IntB);
    }

    public static class ProtectedParent {
        protected String s;
        protected ProtectedParent() { s = "ctor"; }
        public String getViaParent() { return s; }
        protected void setViaParent(String s) { this.s = s; }
    }

    @Test
    public void protectedMembers() {
        ProtectedChild pc = new ProtectedChild();      // Calls protected constructor
        assertEquals("ctor", pc.getViaParent());
        assertEquals("ctor", pc.getViaChildField());   // Reads protected field

        pc.setViaChildMethod("method");                // Calls protected method
        assertEquals("method", pc.getViaParent());
        assertEquals("method", pc.getViaChildField());

        pc.setViaChildField("field");                  // Writes protected field
        assertEquals("field", pc.getViaParent());
        assertEquals("field", pc.getViaChildField());
    }

    public static class OverrideParent {
        public String get() { return "parent"; }
    }

    @Test
    public void overriddenMethod() {
        assertEquals("parent child", new OverrideChild().get());
    }

    @Test
    public void overloadedMethod() {
        OverloadedMethod om = new OverloadedMethod();
        assertEquals(3, om.add(1, 2));
        assertEquals(4, om.add(1.5, 2.5), 0.0001);
        assertEquals("helloworld", om.add("hello", "world"));
    }

    @Test
    public void overloadedCtor() {
        assertEquals("None", new OverloadedCtor().get());
        assertEquals("42", new OverloadedCtor(42).get());
        assertEquals("hello", new OverloadedCtor("hello").get());
    }

    // -------------------------------------------------------------------------------------------

    @Test
    public void returnGood() {
        Return r = new Return();
        r.void_good();
        assertEquals(42, r.primitive_good());
        assertEquals("hello", r.object_good_value());
        assertNull(r.object_good_null());
        assertArrayEquals(new String[] {"hello", "world"}, r.array_good_value());
        assertNull(r.array_good_null());
    }

    @Test
    public void returnVoidBad() {
        thrown.expect(ClassCastException.class);
        thrown.expectMessage("Cannot convert str object to void");
        new Return().void_bad();
    }

    @Test
    public void returnPrimitiveBadValue() {
        thrown.expect(ClassCastException.class);
        thrown.expectMessage("Cannot convert str object to java.lang.Integer");
        new Return().primitive_bad_value();
    }

    @Test
    public void returnPrimitiveBadNull() {
        thrown.expect(NullPointerException.class);
        new Return().primitive_bad_null();
    }

    @Test
    public void returnObjectBad() {
        thrown.expect(ClassCastException.class);
        thrown.expectMessage("Cannot convert int object to java.lang.String");
        new Return().object_bad();
    }

    @Test
    public void returnArrayBadContent() {
        thrown.expect(ClassCastException.class);
        thrown.expectMessage("Cannot convert int object to java.lang.String");
        new Return().array_bad_content();
    }

    @Test
    public void returnArrayBadValue() {
        thrown.expect(ClassCastException.class);
        thrown.expectMessage("Cannot convert str object to java.lang.String[]");
        new Return().array_bad_value();
    }

    // -------------------------------------------------------------------------------------------

    @Test
    public void throwUndeclared0() {
        thrown.expect(UndeclaredThrowableException.class);
        thrown.expectCause(isA(FileNotFoundException.class));
        thrown.expectCause(hasMessage(equalTo("fnf")));
        new Exceptions().undeclared_0();
    }

    @Test
    public void throwUndeclared1() throws EOFException {
        thrown.expect(UndeclaredThrowableException.class);
        thrown.expectCause(isA(FileNotFoundException.class));
        thrown.expectCause(hasMessage(equalTo("fnf")));
        new Exceptions().undeclared_1();
    }

    @Test
    public void throwDeclared() throws EOFException {
        thrown.expect(EOFException.class);
        thrown.expectMessage(equalTo("eof"));
        new Exceptions().declared();
    }

    @Test
    public void throwPython() {
        thrown.expect(PyException.class);
        thrown.expectMessage(equalTo("TypeError: te"));
        new Exceptions().python();
    }

    @Test
    public void throwError() {
        thrown.expect(Error.class);
        thrown.expectMessage(equalTo("e"));
        new Exceptions().error();
    }

    @Test
    public void throwRuntimeException() {
        thrown.expect(RuntimeException.class);
        thrown.expectMessage(equalTo("re"));
        new Exceptions().runtime_exception();
    }

    // -------------------------------------------------------------------------------------------
    
    @Test
    public void modifiers() {
        Modifiers m = new Modifiers();
        assertTrue(m.synced());
        assertFalse(m.unsynced());
    }
}
