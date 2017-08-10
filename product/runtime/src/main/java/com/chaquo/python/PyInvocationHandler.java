package com.chaquo.python;

import java.lang.reflect.*;


/** @deprecated Internal use in proxy.pxi */
public class PyInvocationHandler implements InvocationHandler {
    private PyObject _chaquopyDict;

    public PyInvocationHandler() {
        this._chaquopyDict = Python.getInstance().getBuiltins().callAttr("dict");
    }

    @Override
    public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
        if (method.getName().equals("_chaquopyGetDict")) {
            return _chaquopyDict;
        }

        PyObject self = PyObject.fromJava(proxy);
        if (args == null) {
            args = new Object[0];
        }
        PyObject result = self.callAttr(method.getName(), args);
        return (result == null) ? null : result.toJava(method.getReturnType());
    }

}
