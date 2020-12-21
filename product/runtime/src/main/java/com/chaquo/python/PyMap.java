package com.chaquo.python;

import java.util.*;
import org.jetbrains.annotations.*;


class PyMap extends AbstractMap<PyObject, PyObject> {
    private final PyObject obj;
    private final MethodCache methods;

    public PyMap(PyObject obj) {
        this.obj = obj;
        methods = new MethodCache(obj);
        methods.get("__contains__");
        methods.get("__getitem__");
        methods.get("__iter__");
        methods.get("__len__");
    }

    @Override public @NotNull Set<Entry<PyObject, PyObject>> entrySet() {
        return new AbstractSet<Entry<PyObject, PyObject>>() {
            @Override public int size() {
                return methods.get("__len__").call().toInt();
            }

            @Override public @NotNull Iterator<Entry<PyObject, PyObject>> iterator() {
                return new PyIterator<Entry<PyObject, PyObject>>(methods) {
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
                methods.get("clear").call();
            }
        };
    }


    // === Read methods ======================================================

    @Override public boolean containsKey(Object key) {
        return methods.get("__contains__").call(key).toBoolean();
    }

    @Override public PyObject get(Object key) {
        // For consistency with PyList, use `__getitem__` rather than `get`. Unlike PyList, the
        // Python interface accepts the same parameters as the Java one, so we can allow Python
        // to do the validation.
        try {
            return methods.get("__getitem__").call(key);
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
        methods.get("__setitem__").call(key, value);
        return oldElement;
    }

    @Override public PyObject remove(Object key) {
        return methods.get("pop").call(key, null);
    }

}
