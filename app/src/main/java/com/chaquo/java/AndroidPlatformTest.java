package com.chaquo.java;

import com.chaquo.python.*;
import com.chaquo.python.android.*;
import org.junit.*;

import static org.junit.Assert.*;


public class AndroidPlatformTest {
    @BeforeClass
    public static void androidOnly() {
        Assume.assumeTrue(System.getProperty("java.vendor").toLowerCase().contains("android"));
    }

    @Test
    public void getApplication() {
        assertNotNull(((AndroidPlatform) Python.getPlatform()).getApplication());
    }
}
