package com.chaquo.python;

import java.lang.reflect.*;


/** @deprecated Internal use in proxy.pxi */
public class PyInvocationHandler implements InvocationHandler {
    private PyObject type;
    private PyObject dict;

    public PyInvocationHandler(PyObject type) {
        this.type = type;
    }

    @Override
    public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
        String methodName = method.getName();
        switch (methodName) {
            case "_chaquopyGetType":
                return type;
            case "_chaquopyGetDict":
                return dict;
            case "_chaquopySetDict":
                dict = (PyObject) args[0];
                return null;
            default:
                PyObject self = PyObject.fromJava(proxy);
                if (args == null) {
                    args = new Object[0];
                }
                PyObject result = self.callAttrThrows(methodName, args);
                return (result == null) ? null : result.toJava(method.getReturnType());
        }
    }

}
