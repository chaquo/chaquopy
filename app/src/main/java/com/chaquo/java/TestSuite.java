package com.chaquo.java;

import org.junit.runner.*;
import org.junit.runners.*;

@RunWith(Suite.class)
@Suite.SuiteClasses({
    AndroidPlatformTest.class,
    GenericPlatformTest.class,
    ListTest.class,
    MapTest.class,
    PyObjectTest.class,
    PythonTest.class,
    SetTest.class,
    StaticProxyTest.class
})
public class TestSuite {}
