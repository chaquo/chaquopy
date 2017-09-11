package com.chaquo.java;

import org.junit.runner.*;
import org.junit.runners.*;

@RunWith(Suite.class)
@Suite.SuiteClasses({
    GenericPlatformTest.class,
    PyObjectTest.class,
    PythonTest.class,
    StaticProxyTest.class
})
public class TestSuite {}
