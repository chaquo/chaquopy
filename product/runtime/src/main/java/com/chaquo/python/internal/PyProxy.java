package com.chaquo.python.internal;

import com.chaquo.python.*;


public interface PyProxy {
    PyObject _chaquopyGetDict();
    void _chaquopySetDict(PyObject dict);
}
