package com.chaquo.python;

import java.util.*;

import static com.chaquo.python.ContainerUtils.*;


class PyList extends AbstractList<PyObject> {
    private final PyObject obj;

    public PyList(PyObject obj) {
        this.obj = obj;
        getAttr(obj, "__getitem__");
        getAttr(obj, "__len__");
    }

    // We check bounds before each call, rather than just trying the call and catching the
    // IndexError, because Python accepts indexes which the Java interface doesn't:
    //   * Negative indexes (relative to the end)
    //   * Python `insert` accepts any positive or negative integer: if it's out of bounds then
    //     the element will be added last or first respectively.
    private void checkBounds(int index, int min, int max) {
        if (index < min || index > max) {
            // Similar to Python IndexError message.
            throw new IndexOutOfBoundsException(
                obj.type().get("__name__").toString() + " index out of range");
        }
    }


    // === Read methods ======================================================

    @Override public int size() {
        return callAttr(obj, "__len__").toInt();
    }

    @Override public PyObject get(int index) {
        checkBounds(index, 0, size() - 1);
        return callAttr(obj, "__getitem__", index);
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

    public PyObject set(int index, PyObject element) {
        PyObject oldElement = get(index);  // Includes bounds check.
        callAttr(obj, "__setitem__", index, element);
        return oldElement;
    }

    @Override public void add(int index, PyObject element) {
        checkBounds(index, 0, size());
        callAttr(obj, "insert", index, element);
    }

    @Override public PyObject remove(int index) {
        checkBounds(index, 0, size() - 1);
        return callAttr(obj, "pop", index);
    }

    @Override public void clear() {
        callAttr(obj, "clear");
    }
}
