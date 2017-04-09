package com.chaquo.python;

import java.util.*;

public class PyObject extends AbstractMap<String,PyObject> {
    private PyObject(Object o) {
        // FIXME
    }

    /** Equivalent to Python __call__ */
    public PyObject call(Object... args) {
        // FIXME
        return null;
    }

    /** Equivalent to get(attr).call(args) */
    public PyObject callAttr(String attr, Object... args) {
        return get(attr).call(args);
    }

    /** Equivalent to Python repr() */
    public String repr() {
        // FIXME
        return null;
    }

    /** TODO proxies implement __pyobject__ method which does the reverse */
    public <T> T toJava() {
        // FIXME inspect T to determine requested type. Maybe this can even replace
        // asList etc.?
        return null;
    }

    /*
    public <T> List<T> asList() {}
    public <K,V> Map<K,V> asMap() {}
    public <T> Set<T> asSet() {}
    */


    // ==== Map ====
    // Some pass-through overrides are included so they can carry Javadoc.

    /** Equivalent to Python hasattr() */
    @Override
    public boolean containsKey(Object key) { return super.containsKey(key); }

    /** Equivalent to Python getattr() */
    @Override
    public PyObject get(Object key) { return super.get(key); }

    /** Equivalent to Python setattr() */
    @Override
    public PyObject put(String key, PyObject value) {
        // FIXME
        return null;
    }

    /** Equivalent to Python delattr() */
    @Override
    public PyObject remove(Object key) { return super.remove(key); }

    /** Equivalent to Python dir() */
    @Override
    public Set<String> keySet() { return super.keySet(); }

    @Override
    public Set<Entry<String, PyObject>> entrySet() {
        // FIXME
        return null;
    }


    // === Object ====

    /** Equivalent to Python == operator */
    @Override
    public boolean equals(Object that) {
        // FIXME
        return false;
    }

    /** Equivalent to Python str() */
    @Override
    public String toString() {
        // FIXME
        return null;
    }

    /** Equivalent to Python hash() */
    @Override
    public int hashCode() {
        // FIXME
        return 0;
    }
}
