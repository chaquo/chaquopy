package com.chaquo.python;

import java.lang.reflect.*;


/** @deprecated Internal use in proxy.pxi */
public class PyInvocationHandler implements InvocationHandler, PyProxy {
    private PyObject _chaquopyDict;

    public PyInvocationHandler(PyObject dict) {
        this._chaquopyDict = dict;
    }

    @Override
    public PyObject _chaquopyGetDict() {
        return _chaquopyDict;
    }

    @Override
    public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
        PyObject self = PyObject.fromJava(proxy);
        if (args == null) {
            args = new Object[0];
        }
        return self.callAttr(method.getName(), args).toJava(method.getReturnType());
    }

}
