package com.chaquo.java;

import com.chaquo.python.*;

import org.junit.*;

import static org.junit.Assert.*;


public class GenericPlatformTest {
    @Test
    public void constructor() {
        assertEquals(System.getenv("PYTHONPATH"), new GenericPlatform().getPath());
        assertEquals("foo", new GenericPlatform("foo").getPath());
    }
}
