package com.chaquo.python;

import java.util.*;
import org.jetbrains.annotations.*;


class PySet extends AbstractSet<PyObject> {
    private final PyObject obj;
    private final MethodCache methods;

    public PySet(PyObject obj) {
        this.obj = obj;
        methods = new MethodCache(obj);
        methods.get("__contains__");
        methods.get("__iter__");
        methods.get("__len__");
    }

    // === Read methods ======================================================

    @Override public int size() {
        return methods.get("__len__").call().toInt();
    }

    @Override public boolean contains(Object element) {
        return methods.get("__contains__").call(element).toBoolean();
    }

    @Override public @NotNull Iterator<PyObject> iterator() {
        return new PyIterator<PyObject>(methods) {
            @Override protected PyObject makeNext(PyObject element) {
                return element;
            }
        };
    }


    // === Modification methods ==============================================
    //
    // See note in PyList.

    @Override public boolean add(PyObject element) {
        // Consistently throw an exception for an unmodifiable container, whether it contains
        // the element or not.
        PyObject method = methods.get("add");
        if (contains(element)) {
            return false;
        } else {
            method.call(element);
            return true;
        }
    }

    @Override public boolean remove(Object element) {
        try {
            methods.get("remove").call(element);
            return true;
        } catch (PyException e) {
            if (e.getMessage().startsWith("KeyError:")) {
                return false;
            } else {
                throw e;
            }
        }
    }

    @Override public void clear() {
        methods.get("clear").call();
    }
}
