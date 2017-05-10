package com.chaquo.java;

import com.chaquo.python.*;

import org.junit.*;
import org.junit.rules.*;

import static org.junit.Assert.*;


public class PyObjectTest {
    @Rule
    public ExpectedException thrown = ExpectedException.none();

    private Python python;
    private PyObject builtins;
    private PyObject pyobjecttest;

    @Before
    public void setUp() {
        python = Python.getInstance();
        builtins = python.getBuiltins();
        pyobjecttest = python.getModule("pyobjecttest");
    }

    @Test
    public void getInstance() {
        PyObject sys = python.getModule("sys");
        assertSame(sys, python.getModule("sys"));
        sys.close();
        assertNotSame(sys, python.getModule("sys"));
    }

    @Test
    public void close() {
        pyobjecttest.remove("del_triggered");
        PyObject dt = pyobjecttest.callAttr("DelTrigger");
        assertFalse(pyobjecttest.containsKey("del_triggered"));
        dt.close();
        assertTrue(pyobjecttest.containsKey("del_triggered"));

        thrown.expect(PyException.class);
        thrown.expectMessage("ValueError");
        thrown.expectMessage("closed");
        dt.id();
    }

    @Test
    public void fromJava() {
    }

    @Test
    public void toJava() {
        // FIXME test attempted conversion to primitive type
    }

    @Test
    public void id() {
        PyObject True = builtins.get("True"), False = builtins.get("False");
        assertNotSame(True, False);
        assertNotEquals(True.id(), False.id());
    }

    @Test
    public void type() {
        PyObject True = builtins.get("True"), False = builtins.get("False");
        PyObject bool = builtins.get("bool"), type = builtins.get("type");
        assertSame(True.type(), False.type());
        assertSame(bool, True.type());
        assertSame(type, bool.type());
        assertSame(type, type.type());
        assertNotSame(type, bool);
    }

    @Test
    public void call() {
        PyObject sm = pyobjecttest.get("sum_mul");
        assertEquals(0,  (int)sm.call().toJava(Integer.class));
        assertEquals(3,  (int)sm.call(3).toJava(Integer.class));
        assertEquals(6,  (int)sm.call(1, 2, 3).toJava(Integer.class));
        assertEquals(24, (int)sm.call(6, new Kwarg("mul", 4)).toJava(Integer.class));
        assertEquals(2,  (int)sm.call(1, 2, 3, new Kwarg("div", 3)).toJava(Integer.class));
        assertEquals(10, (int)sm.call(1, 2, 3, new Kwarg("mul", 5),
                                      new Kwarg("div", 3)).toJava(Integer.class));

        PyObject two = sm.call(2), three = sm.call(3), four = sm.call(4);
        assertEquals(14, (int)sm.call(three, four, new Kwarg("mul", two)).toJava(Integer.class));
    }

    @Test
    public void call_invalid_count() {
        thrown.expect(PyException.class);
        thrown.expectMessage("TypeError");
        thrown.expectMessage("got 3");
        builtins.get("sum").call(1, 2, 3);
    }

    @Test
    public void call_invalid_type() {
        thrown.expect(PyException.class);
        thrown.expectMessage("TypeError");
        thrown.expectMessage("unsupported operand");
        pyobjecttest.get("sum_mul").call("hello");
    }

    @Test
    public void call_invalid_kwarg_duplicate() {
        thrown.expect(PyException.class);
        thrown.expectMessage("SyntaxError");
        thrown.expectMessage("repeated");
        pyobjecttest.get("sum_mul").call(6, new Kwarg("mul", 4), new Kwarg("mul", 4));
    }

    @Test
    public void call_invalid_kwarg_order() {
        thrown.expect(PyException.class);
        thrown.expectMessage("SyntaxError");
        thrown.expectMessage("follows keyword");
        pyobjecttest.get("sum_mul").call(new Kwarg("mul", 4), 6);
    }

    @Test
    public void none() {
        assertNull(builtins.get("None"));
        assertTrue(pyobjecttest.callAttr("is_none", (Object)null).toJava(Boolean.class));
        assertTrue(pyobjecttest.callAttr("is_none", (Object[])null).toJava(Boolean.class));
        assertFalse(pyobjecttest.callAttr("is_none", 42).toJava(Boolean.class));
    }

    // ==== Map ==============================================================

    @Test
    public void clear() {
        PyObject so = pyobjecttest.callAttr("SimpleObject");
        assertFalse(so.isEmpty());
        so.clear();
        assertTrue(so.isEmpty());
        so.put("test", 1);
        assertFalse(so.isEmpty());
        so.clear();
        assertTrue(so.isEmpty());
    }

    @Test
    public void containsKey() {
        PyObject so = pyobjecttest.callAttr("SimpleObject");
        assertTrue(so.containsKey("one"));
        assertFalse(so.containsKey("six"));
        assertTrue(so.containsKey("two"));
        assertFalse(so.containsKey("nine"));
    }

    @Test
    public void containsKey_invalid_null() {
        thrown.expect(PyException.class);
        thrown.expectMessage("ValueError");
        thrown.expectMessage("null");
        assertFalse(builtins.containsKey(null));
    }


    @SuppressWarnings("SuspiciousMethodCalls")
    @Test
    public void containsKey_invalid_type() {
        thrown.expect(PyException.class);
        thrown.expectMessage("TypeError");
        thrown.expectMessage("not a String");
        builtins.containsKey(42);
    }

    /* FIXME need .equals
    @SuppressWarnings("SuspiciousMethodCalls")
    @Test
    public void containsValue() {
        PyObject so = pyobjecttest.callAttr("SimpleObject");
        assertTrue(so.containsValue(1));
        assertFalse(so.containsValue(6));
        assertTrue(so.containsValue(2));
        assertFalse(so.containsValue(9));
        assertFalse(so.containsValue(null));
    }
    */

    @Test
    public void get() {
        // FIXME get nonexistent should return null
    }

    @Test
    public void put() {
        // FIXME
    }

    @Test
    public void remove() {
        assertTrue(pyobjecttest.containsKey("to_remove"));
        assertSame(builtins.get("abs"), pyobjecttest.remove("to_remove"));
        assertFalse(pyobjecttest.containsKey("to_remove"));
        assertNull(pyobjecttest.remove("to_remove"));
    }

    // ==== Object ===========================================================

    @SuppressWarnings("UnusedAssignment")
    @Test
    public void finalize_close() {
        pyobjecttest.remove("del_triggered");
        PyObject dt = pyobjecttest.callAttr("DelTrigger");
        assertFalse(pyobjecttest.containsKey("del_triggered"));
        dt = null;
        System.gc();
        System.runFinalization();
        assertTrue(pyobjecttest.containsKey("del_triggered"));
    }

}
