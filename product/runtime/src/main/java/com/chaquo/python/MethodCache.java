package com.chaquo.python;

import java.util.*;

class MethodCache {

    private PyObject obj;
    private Map<String, PyObject> cache = new HashMap<>();

    public MethodCache(PyObject obj) {
        this.obj = obj;
    }

    public PyObject get(String name) {
        PyObject value = cache.get(name);
        if (value == null) {
            value = obj.get(name);
            if (value == null) {
                // Same wording as Python AttributeError.
                throw new UnsupportedOperationException(
                    String.format("'%s' object has no attribute '%s'",
                                  obj.type().get("__name__"), name));
            }
            cache.put(name, value);
        }
        return value;
    }
}
