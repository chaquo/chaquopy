package com.chaquo.python;

import java.util.*;

import static com.chaquo.python.ContainerUtils.callAttr;
import static com.chaquo.python.ContainerUtils.getAttr;

class PySet extends AbstractSet<PyObject> {
    private final PyObject obj;

    public PySet(PyObject obj) {
        this.obj = obj;
        getAttr(obj, "__contains__");
        getAttr(obj, "__iter__");
        getAttr(obj, "__len__");
    }

    // === Read methods ======================================================

    @Override public int size() {
        return callAttr(obj, "__len__").toInt();
    }

    @Override public boolean contains(Object element) {
        return callAttr(obj, "__contains__", element).toBoolean();
    }

    @Override public Iterator<PyObject> iterator() {
        return new PyIterator<PyObject>(obj) {
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
        PyObject method = getAttr(obj, "add");
        if (contains(element)) {
            return false;
        } else {
            method.call(element);
            return true;
        }
    }

    @Override public boolean remove(Object element) {
        // Consistently throw an exception for an unmodifiable container, whether it contains
        // the element or not.
        PyObject method = getAttr(obj, "remove");
        if (contains(element)) {
            method.call(element);
            return true;
        } else {
            return false;
        }
    }

    @Override public void clear() {
        callAttr(obj, "clear");
    }
}
