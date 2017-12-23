package com.chaquo.python.static_proxy;

import com.chaquo.python.*;
import com.chaquo.python.internal.*;

public class WrongExtends extends Exception implements StaticProxy {
    public PyObject _chaquopyGetDict() { return null; }
    public void _chaquopySetDict(PyObject dict) {}
}
