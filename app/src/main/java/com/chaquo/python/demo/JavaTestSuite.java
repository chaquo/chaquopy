package com.chaquo.python.demo;

import com.chaquo.java.*;

import org.junit.runner.*;
import org.junit.runners.*;

@RunWith(Suite.class)
@Suite.SuiteClasses({
    // GenericPlatformTest won't work on Android.
    PyObjectTest.class,
    PythonTest.class
})

public class JavaTestSuite {}
