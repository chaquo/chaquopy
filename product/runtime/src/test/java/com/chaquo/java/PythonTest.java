package com.chaquo.java;
import com.chaquo.python.*;

import org.junit.*;

import static org.junit.Assert.assertEquals;


public class PythonTest {
    private Python python;

    @Before
    public void setUp() {
        python = Python.getInstance();
    }

    @Test
    public void add() {
        assertEquals(42, python.add(0));
        assertEquals(45, python.add(3));
    }
}
