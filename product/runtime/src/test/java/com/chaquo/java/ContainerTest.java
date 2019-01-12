package com.chaquo.java;

import com.chaquo.python.*;
import org.junit.*;
import org.junit.rules.*;

public class ContainerTest {
    @Rule
    public ExpectedException thrown = ExpectedException.none();

    protected Python py = Python.getInstance();
    protected PyObject mod = py.getModule("chaquopy.test_java.container_test");

    protected void expectUnsupported(String type, String attr) {
        thrown.expect(UnsupportedOperationException.class);
        thrown.expectMessage("'" + type + "' object has no attribute '" + attr + "'");
    }
}
