package com.chaquo.java;
import com.chaquo.python.*;

import org.junit.*;
import org.junit.rules.*;

import static org.junit.Assert.*;


public class PythonTest {
    private Python python;

    @Rule
    public ExpectedException thrown = ExpectedException.none();

    @Before
    public void setUp() {
        python = Python.getInstance();
    }

    @Test
    public void getInstance() {
        assertSame(python, Python.getInstance());
    }

    @Test
    public void start() {
        thrown.expect(IllegalStateException.class);
        thrown.expectMessage("Python already started");
        Python.start(new GenericPlatform());
    }

    @Test
    public void getModule() {
        PyObject sys = python.getModule("sys");
        String sysStr = sys.toString();
        assertTrue(sysStr, sysStr.contains("module 'sys'"));

        thrown.expect(PyException.class);
        thrown.expectMessage("No module named");
        python.getModule("nonexistent");
    }

    @Test
    public void hello() {
        assertEquals("hello world", python.hello("world"));
        assertEquals("hello ", python.hello(""));
    }

    @Test
    public void add() {
        assertEquals(42, python.add(0));
        assertEquals(45, python.add(3));
    }
}
