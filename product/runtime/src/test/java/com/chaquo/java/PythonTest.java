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
        python.getModule("foo");
    }

    @Test
    public void getBuiltins() {
        PyObject builtins = python.getBuiltins();
        assertTrue(builtins.containsKey("open"));
        assertTrue(builtins.containsKey("dict"));
        assertTrue(builtins.containsKey("None"));
        assertFalse(builtins.containsKey("foo"));
    }
}
