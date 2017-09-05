package com.chaquo.java;

import org.junit.*;
import static_proxy.basic.*;

import static org.junit.Assert.*;


public class StaticProxyTest {

    @Test
    public void adder() {
        Adder a1 = new Adder(1);
        Adder a2 = new Adder(2);
        assertEquals(6, a1.add(5));
        assertEquals(7, a2.add(5));
    }

}
