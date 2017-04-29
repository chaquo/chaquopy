package com.chaquo.python;

import java.lang.ref.*;
import java.util.*;


/** Proxy for an object in the Python virtual machine */
public class PyObject extends AbstractMap<String,PyObject> implements AutoCloseable {
    private static Map<Long, WeakReference<PyObject>> cache = new HashMap<>();

    /** @hide (used in chaquopy_java.pyx) */
    public long obj;

    /** @hide (used in chaquopy_java.pyx) */
    public static PyObject getInstance(long obj) {
        WeakReference<PyObject> wr = cache.get(obj);
        if (wr != null) {
            PyObject po = wr.get();
            if (po == null) {
                cache.remove(obj);
            } else {
                return po;
            }
        }
        PyObject po = new PyObject(obj);
        cache.put(obj, new WeakReference<>(po));
        return po;
    }

    private PyObject(long obj) {
        this.obj = obj;
    }

    /** Releases the reference to the Python object. Unless the object represents an expensive
     * resource, there's no need to call this method manually: it will be called automatically when
     * the PyObject is garbage-collected. */
    public native void close();

    /** If the object already has a PyObject counterpart, it will be returned */
    public static PyObject fromJava(Object o) {
        // FIXME
        return null;
    }

    /** TODO proxies implement interface with __pyobject__ method which does the reverse */
    public <T> T toJava() {
        // FIXME inspect T to determine requested type. If the object is Java-owned and
        // isinstance(T), simply return it. This makes asList etc. unnecessary, but need to think
        // through the implications of having multiple Java objects for each PyObject.
        return null;
    }

    /** Equivalent to Python type() */
    public native PyObject type();

    /** Equivalent to Python () syntax. */ // TODO kwargs
    public native PyObject call(Object... args);

    /** Equivalent to {@link #get}(attr).{@link #call}(args) */
    public PyObject callAttr(String attr, Object... args) {
        return get(attr).call(args);
    }

    // ==== Map ====

    /** Equivalent to Python hasattr() */
    @Override
    public boolean containsKey(Object key) {
        // FIXME
        return false;
    }

    /** Equivalent to Python getattr() */
    @Override
    public PyObject get(Object key) {
        // FIXME
        return null;
    }

    /** Equivalent to Python setattr() */
    @Override
    public PyObject put(String key, PyObject value) {
        // FIXME
        return null;
    }

    /** Equivalent to Python setattr() */
    public PyObject put(String key, Object value) {
        return put(key, fromJava(value));
    }

    /** Equivalent to Python delattr() */
    @Override
    public PyObject remove(Object key) {
        // FIXME
        return null;
    }

    /** Equivalent to Python dir() */
    @Override
    public Set<String> keySet() {
        return super.keySet();      // Override just here to carry the Javadoc
    }

    @Override
    public Set<Entry<String, PyObject>> entrySet() {
        // FIXME
        return null;
    }


    // === Object ====

    /** Equivalent to Python == operator */
    @Override
    public native boolean equals(Object that);

    /** Equivalent to Python str() */
    @Override
    public native String toString();

    /** Equivalent to Python repr() */
    public native String repr();

    /** Equivalent to Python hash() */
    @Override
    public native int hashCode();

    /** Calls {@link #close}() */
    @Override
    protected void finalize() throws Throwable {
        close();
        super.finalize();
    }
}
