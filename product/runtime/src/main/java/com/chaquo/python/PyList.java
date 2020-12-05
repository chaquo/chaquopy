package com.chaquo.python;

import java.util.*;


class PyList extends AbstractList<PyObject> {
    private final PyObject obj;
    private final MethodCache methods;

    public PyList(PyObject obj) {
        this.obj = obj;
        methods = new MethodCache(obj);
        methods.get("__getitem__");
        methods.get("__len__");
    }

    // Python accepts negative indices, but the Java interface should reject them. We don't
    // usually check the upper bound, because that would make a redundant call to `__len__`.
    // Instead, the caller should catch IndexError.
    private void checkLowerBound(int index) {
        if (index < 0) {
            throw outOfBounds(index);
        }
    }

    private RuntimeException maybeOutOfBounds(int index, PyException e) {
        if (e.getMessage().startsWith("IndexError:")) {
            return outOfBounds(index);
        } else {
            return e;
        }
    }

    private IndexOutOfBoundsException outOfBounds(int index) {
        // Same wording as ArrayList exception.
        return new IndexOutOfBoundsException(
            "Invalid index " + index + ", size is " + size());
    }


    // === Read methods ======================================================

    @Override public int size() {
        return methods.get("__len__").call().toInt();
    }

    @Override public PyObject get(int index) {
        checkLowerBound(index);
        try {
            return methods.get("__getitem__").call(index);
        } catch (PyException e) {
            throw maybeOutOfBounds(index, e);
        }
    }


    // === Modification methods ==============================================
    //
    // Ideally `set` and `add` would be able to take any object, to save the user having to
    // call PyObject.fromJava manually. But we can't replace or overload the methods with
    // versions which take Object, because that causes the error "set(int,Object) in PyList and
    // set(int,E) in AbstractList have the same erasure, yet neither overrides the other". It
    // makes no difference whether we use AbstractList or implement List directly.
    //
    // We got away with this when overloading PyObject.put, because its key parameter is a
    // String, not an Object, so it doesn't have the same erasure as the base class method in
    // Map.
    //
    // I also tried the reverse approach of extending List<Object>. In this case, the
    // modification methods are no problem. The read methods *almost* work because the
    // covariance rule allows `get` to still return a PyObject. But that rule doesn't apply to
    // `iterator`: it has to return Iterator<Object>, which would force the user to cast the
    // elements to PyObject when using them in a for-each loop. It can't return
    // Iterator<PyObject>, even though this is in fact substitutable for Iterator<Object>,
    // because there's no way to express that fact in the language.
    //
    // Since users of this API are more likely to be reading containers than modifying them,
    // we'll prioritize accordingly.
    //
    // A possible future improvement would be to add a PyObject method:
    //     List<T> asList(Class<T> elementType)
    // which would allow the PyList to call toJava and fromJava automatically.

    public PyObject set(int index, PyObject element) {
        PyObject oldElement = get(index);  // Includes bounds check.
        methods.get("__setitem__").call(index, element);
        return oldElement;
    }

    @Override public void add(int index, PyObject element) {
        // For this method we need to check the upper bound as well, because `insert` accepts
        // any index and truncates it to the length of the sequence.
        checkLowerBound(index);
        if (index > size()) {
            throw outOfBounds(index);
        }
        methods.get("insert").call(index, element);  // Never throws IndexError.
    }

    @Override public PyObject remove(int index) {
        checkLowerBound(index);
        try {
            return methods.get("pop").call(index);
        } catch (PyException e) {
            throw maybeOutOfBounds(index, e);
        }
    }

    @Override public void clear() {
        methods.get("clear").call();
    }
}
