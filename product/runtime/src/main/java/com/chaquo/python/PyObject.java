package com.chaquo.python;

import java.lang.ref.*;
import java.util.*;


/** Proxy for a Python object.
 * <ul>
 *     <li>Python None is represented by Java null. All other values can be converted to their Java
 *     equivalents using {@link #toJava}.</li>
 *     <li>If the same object is retrieved from Python multiple times, the same PyObject will be
 *     returned (unless {@link #close}() has been called).</li>
 * </ul>
 *
 * Unless otherwise specified, methods in this class throw {@link PyException} on failure.
 * . */
public class PyObject extends AbstractMap<String,PyObject> implements AutoCloseable {
    private static final Map<Long, WeakReference<PyObject>> cache = new HashMap<>();

    /** @hide
     * Used in chaquopy_java.pyx */
    public long addr;

    /** @hide
     * Used in chaquopy_java.pyx. Always called with the GIL. */
    public static PyObject getInstance(long addr) {
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
    private PyObject(long addr) {
        this.addr = addr;
        openNative();
        cache.put(addr, new WeakReference<>(this));
    }
    private native void openNative();


    /** Releases the reference to the Python object. Unless the object represents an expensive
     * resource, there's no need to call this method manually: it will be called automatically when
     * the PyObject is garbage-collected.
     *
     * After calling close(), the PyObject can no longer be used. If there are no other references
     * to the underlying object, it may be destroyed by Python. If it continues to exist and is
     * retrieved by Java code again, a different PyObject will be returned. */
    public void close() {
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
    private native void closeNative();


    /** Gives the given Java object a presence in the Python virtual machine.
     * There's usually no need to call this method manually: it will be called as necessary when
     * passing an object to Python using {@link #call} or {@link #put(String, Object)}.
     * <ul>
     *     <li>If the given object is of an immutable value type such as Boolean, Integer or String,
     *     an equivalent Python object will be created.</li>
     *     <li>If the given object is itself a proxy for a Python object, the original Python object
     *     will be returned.</li>
     *     <li>Otherwise, a proxy object will be created, exposing all the methods and fields of the
     *     given object to Python code.</li>
     * </ul> */
    public static native PyObject fromJava(Object o);
    // TODO #5154... If the given object implements List, Map or Set, the proxy object will also
    // implement the corresponding Python methods (__len__, __getitem__, etc.).

    /** Attempts to "cast" the Python object to the given Java type.
     * <ul>
     *     <li>If the given type is an immutable value type such as Boolean, Integer or String,
     *     the call will succeed if the Python object is of a compatible type.</li>
     *     <li>If the Python object is itself a proxy for a Java object of the given type, the
     *     original Java object will be returned.</li>
     *     <li>Otherwise, a <code>ClassCastException</code> will be thrown.</li>
     * </ul> */
    public native <T> T toJava(Class<T> klass);
    // TODO  *     <li>The basic container interfaces: List, Map and Set. The toJava call will always
    // #5154 *     succeed, returning a proxy object which calls the corresponding Python methods (__len__,
    //       *     __getitem__, etc.).</li>
    // Not sure whether to do this with java.lang.reflect.Proxy or with pre-defined classes PyList,
    // PyMap, etc. Actually, the latter could be implemented entirely in Java, which would also
    // serve as a good example for how to make a manual static proxy.

    /** Equivalent to Python id() */
    public native long id();

    /** Equivalent to Python type() */
    public native PyObject type();

    /** Equivalent to Python () syntax. */ // TODO kwargs
    public native PyObject call(Object... args);

    /** Equivalent to {@link #get}(attr).{@link #call}(args) */
    public PyObject callAttr(String attr, Object... args) {
        return get(attr).call(args);
    }

    // ==== Map ==============================================================

    /** Equivalent to Python hasattr() */
    @Override public native boolean containsKey(Object key);

    /** Equivalent to Python getattr() */
    @Override public native PyObject get(Object key);

    /** Equivalent to Python setattr() */
    @Override public PyObject put(String key, PyObject value) {
        return put(key, (Object)value);
    }

    /** Equivalent to Python setattr() */
    public native PyObject put(String key, Object value);

    /** Equivalent to Python delattr() */
    @Override public native PyObject remove(Object key);

    /** Equivalent to Python dir() */
    @Override
    public Set<String> keySet() {
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

                    @Override public boolean hasNext() {
                        return i < keys.size();
                    }

                    @Override public Entry<String, PyObject> next() {
                        if (! hasNext()) throw new NoSuchElementException();
                        Entry<String, PyObject> entry = new Entry<String, PyObject>() {
                            String key = keys.get(i);
                            @Override public String getKey()     { return key; }
                            @Override public PyObject getValue() { return get(key); }
                            @Override public PyObject setValue(PyObject newValue) {
                                return put(key, newValue);
                            }
                        };
                        i += 1;
                        return entry;
                    }

                    @Override public void remove() {
                        PyObject.this.remove(keys.get(i-1));
                    }
                };
            }
        };
    }

    private native List<String> dir();


    // === Object ============================================================

    /** Equivalent to Python == operator */
    @Override public native boolean equals(Object that);

    /** Equivalent to Python str() */
    @Override public native String toString();

    /** Equivalent to Python repr() */
    public native String repr();

    /** Equivalent to Python hash() */
    @Override public native int hashCode();

    /** Calls {@link #close}() */
    @Override
    protected void finalize() throws Throwable {
        close();
        super.finalize();
    }
}
