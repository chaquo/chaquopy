package com.chaquo.java;

import com.chaquo.python.*;

import org.junit.*;
import org.junit.rules.*;

import static org.junit.Assert.*;


public class GenericPlatformTest {
    @Rule
    public ExpectedException thrown = ExpectedException.none();

    @Test
    public void constructor() {
        if (System.getProperty("java.vendor").toLowerCase().contains("android")) {
            thrown.expect(RuntimeException.class);
            thrown.expectMessage("Cannot use GenericPlatform on Android");
        }
        assertEquals(System.getenv("PYTHONPATH"), new GenericPlatform().getPath());
        assertEquals("foo", new GenericPlatform().setPath("foo").getPath());
    }
}
