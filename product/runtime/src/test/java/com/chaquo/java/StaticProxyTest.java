package com.chaquo.java;

import org.junit.*;
import static_proxy.basic.*;

import static org.junit.Assert.*;


public class StaticProxyTest {

    @Test
    public void basic() {
        BasicAdder a1 = new BasicAdder(1);
        BasicAdder a2 = new BasicAdder(2);
        assertEquals(6, a1.add(5));
        assertEquals(7, a2.add(5));
    }

    @Test
    public void overloadedMethod() {
        OverloadedAdder oa = new OverloadedAdder();
        assertEquals(3, oa.add(1, 2));
        assertEquals(4, oa.add(1.5, 2.5), 0.0001);
        assertEquals("helloworld", oa.add("hello", "world"));
    }

    @Test
    public void overloadedCtor() {
        assertEquals("None", new OverloadedCtor().get());
        assertEquals("42", new OverloadedCtor(42).get());
        assertEquals("hello", new OverloadedCtor("hello").get());
    }

}
