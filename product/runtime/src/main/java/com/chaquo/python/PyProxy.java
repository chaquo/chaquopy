package com.chaquo.python;

/** @deprecated Internal use in class.pxi */
public interface PyProxy {
    PyObject _chaquopyGetDict();
    void _chaquopySetDict(PyObject dict);
}
