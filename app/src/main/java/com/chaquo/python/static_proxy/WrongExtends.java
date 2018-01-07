package com.chaquo.python.static_proxy;

import com.chaquo.python.*;

@SuppressWarnings("deprecation")
public class WrongExtends extends Exception implements StaticProxy {
    public PyObject _chaquopyGetDict() { return null; }
    public void _chaquopySetDict(PyObject dict) {}
}
