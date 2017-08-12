package com.chaquo.python;

import java.lang.reflect.*;


/** @deprecated Internal use in proxy.pxi */
public class PyInvocationHandler implements InvocationHandler {
    private PyObject _chaquopyDict;

    @Override
    public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
        String methodName = method.getName();
        switch (methodName) {
            case "_chaquopyGetDict":
                return _chaquopyDict;
            case "_chaquopySetDict":
                _chaquopyDict = (PyObject) args[0];
                return null;
            default:
                PyObject self = PyObject.fromJava(proxy);
                if (args == null) {
                    args = new Object[0];
                }
                PyObject result = self.callAttr(methodName, args);
                return (result == null) ? null : result.toJava(method.getReturnType());
        }
    }

}
