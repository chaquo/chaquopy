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
        thrown.expectMessage("closed");
        dt.id();
    }

    @Test
    @SuppressWarnings("UnusedAssignment")
    public void finalize_close() {
        pyobjecttest.remove("del_triggered");
        PyObject dt = pyobjecttest.callAttr("DelTrigger");
        assertFalse(pyobjecttest.containsKey("del_triggered"));
        dt = null;
        System.gc();
        System.runFinalization();
        assertTrue(pyobjecttest.containsKey("del_triggered"));
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
        assertNotSame(True.type(), bool.type());
    }


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

}
