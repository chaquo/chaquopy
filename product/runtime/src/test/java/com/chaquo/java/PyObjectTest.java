package com.chaquo.java;

import com.chaquo.python.*;

import org.junit.*;

import static org.junit.Assert.*;


public class PyObjectTest {
    private Python python;

    @Before
    public void setUp() {
        python = Python.getInstance();
    }

    @Test
    public void getInstance() {
        PyObject sys = python.getModule("sys");
        assertSame(sys, python.getModule("sys"));

        // This is not guaranteed to work:
        //   * System.gc() is not guaranteed to destroy the first object.
        //   * If it does, the second object is not guaranteed to have a different identityHashCode.
        int id = System.identityHashCode(sys);
        sys = null;
        System.gc();
        sys = python.getModule("sys");
        assertNotEquals(id, System.identityHashCode(sys));
    }
}
