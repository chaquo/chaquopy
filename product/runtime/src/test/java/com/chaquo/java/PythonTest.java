package com.chaquo.java;

import com.chaquo.python.*;
import org.junit.*;
import org.junit.rules.*;
import org.junit.runners.*;

import static org.junit.Assert.*;


@FixMethodOrder(MethodSorters.NAME_ASCENDING)
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
        Python.start(null);
    }

    @Test
    public void getPlatform() {
        assertNotNull(Python.getPlatform());
    }

    @Test
    public void isStarted() {
        assertTrue(Python.isStarted());
    }

    @Test
    public void getModule() {
        PyObject os = python.getModule("os");
        String osStr = os.toString();
        assertTrue(osStr, osStr.contains("module 'os'"));
        PyObject osPath = python.getModule("os.path");
        assertSame(osPath, os.get("path"));

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
