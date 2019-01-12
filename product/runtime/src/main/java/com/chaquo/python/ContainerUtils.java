package com.chaquo.python;

class ContainerUtils {

    public static PyObject getAttr(PyObject obj, String name) {
        PyObject value = obj.get(name);
        if (value == null) {
            // Same wording as Python AttributeError.
            throw new UnsupportedOperationException(
                String.format("'%s' object has no attribute '%s'",
                              obj.type().get("__name__"), name));
        }
        return value;
    }

    public static PyObject callAttr(PyObject obj, String name, Object... args) {
        return getAttr(obj, name).call(args);
    }

}
