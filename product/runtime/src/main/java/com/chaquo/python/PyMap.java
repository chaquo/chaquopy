package com.chaquo.python;

import java.util.*;

import static com.chaquo.python.ContainerUtils.*;


class PyMap extends AbstractMap<PyObject, PyObject> {
    private final PyObject obj;

    public PyMap(PyObject obj) {
        this.obj = obj;
        getAttr(obj, "__contains__");
        getAttr(obj, "__getitem__");
        getAttr(obj, "__iter__");
        getAttr(obj, "__len__");
    }

    @Override public Set<Entry<PyObject, PyObject>> entrySet() {
        return new AbstractSet<Entry<PyObject, PyObject>>() {
            @Override public int size() {
                return callAttr(obj, "__len__").toInt();
            }

            @Override public Iterator<Entry<PyObject, PyObject>> iterator() {
                return new PyIterator<Entry<PyObject, PyObject>>(obj) {
                    @Override protected Entry<PyObject, PyObject> makeNext(final PyObject key) {
                        return new Entry<PyObject, PyObject>() {
                            @Override public PyObject getKey() { return key; }
                            @Override public PyObject getValue() { return get(key); }
                            @Override public PyObject setValue(PyObject value) {
                                return put(key, value);
                            }
                        };
                    }
                };
            }

            @Override public void clear() {
                callAttr(obj, "clear");
            }
        };
    }


    // === Read methods ======================================================

    @Override public boolean containsKey(Object key) {
        return callAttr(obj, "__contains__", key).toBoolean();
    }

    @Override public PyObject get(Object key) {
        // For consistency with PyList, use `__getitem__` rather than `get`. Unlike PyList, the
        // Python interface accepts the same parameters as the Java one, so we can allow Python
        // to do the validation.
        try {
            return callAttr(obj, "__getitem__", key);
        } catch (PyException e) {
            if (e.getMessage().startsWith("KeyError:")) {
                return null;
            } else {
                throw e;
            }
        }
    }


    // === Modification methods ==============================================
    //
    // See note in PyList.

    @Override public PyObject put(PyObject key, PyObject value) {
        PyObject oldElement = get(key);
        callAttr(obj, "__setitem__", key, value);
        return oldElement;
    }

    @Override public PyObject remove(Object key) {
        return callAttr(obj, "pop", key, null);
    }

}
