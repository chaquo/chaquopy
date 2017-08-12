package com.chaquo.python;

/** @deprecated Internal use in class.pxi */
public interface PyProxy {
    PyObject _chaquopyGetDict();
    PyObject _chaquopySetDict(PyObject dict);
}
