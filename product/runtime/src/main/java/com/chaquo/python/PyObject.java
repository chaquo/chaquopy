package com.chaquo.python;

import java.lang.ref.*;
import java.util.*;


/** Proxy for a Python object. If the same object is retrieved from Python multiple times,
 * the same PyObject will be returned (but see the notes on {@link #close}(). */
public class PyObject extends AbstractMap<String,PyObject> implements AutoCloseable {
    private static final Map<Long, WeakReference<PyObject>> cache = new HashMap<>();

    /** @hide (used in chaquopy_java.pyx) */
    public long addr;

    /** @hide (used in chaquopy_java.pyx)
     * Always called with the GIL */
    public static PyObject getInstance(long addr) throws PyException {
        synchronized (cache) {
            WeakReference<PyObject> wr = cache.get(addr);
            if (wr != null) {
                // wr.get() will return null if the PyObject is unreachable but it has not yet been
                // removed it from the cache. In that case, the constructor call below will
                // overwrite it.
                PyObject po = wr.get();
                if (po != null) return po;
            }
            return new PyObject(addr);
        }
    }

    /** Always called with the GIL and the cache lock */
    private PyObject(long addr) throws PyException {
        this.addr = addr;
        openNative();
        cache.put(addr, new WeakReference<>(this));
    }
    private native void openNative() throws PyException;


    /** Releases the reference to the Python object. Unless the object represents an expensive
     * resource, there's no need to call this method manually: it will be called automatically when
     * the PyObject is garbage-collected.
     *
     * After calling close(), the PyObject can no longer be used. If there are no other references
     * to the underlying object, it may be destroyed by Python. If it continues to exist and is
     * retrieved by Java code again, a different PyObject will be returned. */
    public void close() throws PyException {
        if (addr == 0) return;
        synchronized (cache) {
            WeakReference<PyObject> wr = cache.remove(addr);
            if (wr != null) {
                PyObject po = wr.get();
                if (po != null && po != this) {
                    // We're running in the finalizer and we've already been replaced by a new PyObject.
                    cache.put(addr, wr);
                }
            }
        }
        // Don't take the GIL within the cache lock, because most other methods do it in the
        // opposite order.
        closeNative();
        addr = 0;
    }
    private native void closeNative() throws PyException;


    /** If the object already has a PyObject counterpart, it will be returned */
    public static PyObject fromJava(Object o) throws PyException {
        // FIXME
        return null;
    }

    /** TODO proxies implement interface with __pyobject__ method which does the reverse */
    public <T> T toJava() throws PyException {
        // FIXME inspect T to determine requested type. If the object is Java-owned and
        // isinstance(T), simply return it. This makes asList etc. unnecessary, but need to think
        // through the implications of having multiple Java objects for each PyObject.
        return null;
    }

    /** Equivalent to Python id() */
    public native long id() throws PyException;

    /** Equivalent to Python type() */
    public native PyObject type() throws PyException;

    /** Equivalent to Python () syntax. */ // TODO kwargs
    public native PyObject call(Object... args) throws PyException;

    /** Equivalent to {@link #get}(attr).{@link #call}(args) */
    public PyObject callAttr(String attr, Object... args) throws PyException {
        return get(attr).call(args);
    }

    // ==== Map ====

    /** Equivalent to Python hasattr() */
    @Override public native boolean containsKey(Object key) throws PyException;

    /** Equivalent to Python getattr() */
    @Override public native PyObject get(Object key) throws PyException;

    /** Equivalent to Python setattr() */
    @Override public native PyObject put(String key, PyObject value) throws PyException;

    /** Equivalent to Python setattr() */
    public PyObject put(String key, Object value) throws PyException {
        // This can't be the only signature, because it would overload rather than override the base
        // class put(PyObject) method which throws an unimplemented exception.
        return put(key, fromJava(value));
    }

    /** Equivalent to Python delattr() */
    @Override public native PyObject remove(Object key) throws PyException;

    /** Equivalent to Python dir() */
    @Override
    public Set<String> keySet() throws PyException {
        return super.keySet();  // Override just to carry the Javadoc
    }

    @Override
    public Set<Entry<String, PyObject>> entrySet() {
        return new AbstractSet<Entry<String, PyObject>>() {
            @Override public int size() { return dir().size(); }

            @Override public Iterator<Entry<String, PyObject>> iterator() {
                return new Iterator<Entry<String, PyObject>>() {
                    List<String> keys = dir();
                    int i = 0;

                    @Override public boolean hasNext() { return i < keys.size(); }

                    @Override public Entry<String, PyObject> next() {
                        if (! hasNext()) throw new NoSuchElementException();
                        Entry<String, PyObject> entry = new Entry<String, PyObject>() {
                            String key = keys.get(i);
                            @Override public String getKey()     { return key; }
                            @Override public PyObject getValue() { return get(key); }
                            @Override public PyObject setValue(PyObject newValue) {
                                PyObject oldValue = getValue();
                                put(key, newValue);
                                return oldValue;
                            }
                        };
                        i += 1;
                        return entry;
                    }

                    @Override public void remove() { PyObject.this.remove(keys.get(i)); }
                };
            }
        };
    }

    private native List<String> dir() throws PyException;


    // === Object ====

    /** Equivalent to Python == operator */
    @Override public native boolean equals(Object that) throws PyException;

    /** Equivalent to Python str() */
    @Override public native String toString() throws PyException;

    /** Equivalent to Python repr() */
    public native String repr() throws PyException;

    /** Equivalent to Python hash() */
    @Override public native int hashCode() throws PyException;

    /** Calls {@link #close}() */
    @Override
    protected void finalize() throws Throwable {
        close();
        super.finalize();
    }
}
