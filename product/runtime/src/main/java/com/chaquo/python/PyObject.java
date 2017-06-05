package com.chaquo.python;

import java.lang.ref.*;
import java.util.*;


/** Proxy for a Python object.
 *
 * * Python `None` is represented by Java `null`. Other `PyObject`s can be converted to their Java
 *   equivalents using {@link #toJava toJava()}.
 * * If the same object is retrieved from Python multiple times, it will be represented by the same
 *   PyObject (unless {@link #close} is called).
 *
 * Unless otherwise specified, methods in this class throw {@link PyException} on failure.*/
public class PyObject extends AbstractMap<String,PyObject> implements AutoCloseable {
    private static final Map<Long, WeakReference<PyObject>> cache = new HashMap<>();

    /** @deprecated Internal use in conversion.pxi */
    public long addr;

    /** @deprecated Internal use in chaquopy_java.pyx.
     * Always called with the GIL. */
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
    @SuppressWarnings("deprecation")
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
     * After calling `close()`, the PyObject can no longer be used. If there are no other
     * references to the underlying object, it may be destroyed by Python. If it continues to exist
     * and is retrieved by Java code again, a different PyObject will be returned. */
    @SuppressWarnings("deprecation")
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
     * There's usually no need to call this method manually: it will be called automatically by the
     * methods of this class which take `Object` parameters.
     *
     * * If the given object is of an immutable value type such as `Boolean`, `Integer` or `String`,
     *   an equivalent Python object will be created.
     * * If the given object is itself a proxy for a Python object, the original Python object
     *   will be returned.
     * * Otherwise, a proxy object will be created, exposing all the methods and fields of the
     *   Java object to Python code. */
    //
    // TODO #5154... If the given object implements `List`, `Map` or `Set`, the proxy object will
    // implement the corresponding Python methods (`__len__`, `__getitem__`, etc.).
    public static native PyObject fromJava(Object o);

    /** Attempts to view the Python object as the given Java type. For example.
     * `toJava(String.class)` will attempt to view the object as a String.
     *
     * * If the given type is an immutable value type such as `Boolean`, `Integer` or `String`,
     *   and the Python object is of a compatible type, an equivalent object will be returned.
     * * If the Python object is itself a proxy for a Java object of the given type, the
     *   original Java object will be returned.
     * * Otherwise, a `ClassCastException` will be thrown. */
    //
    // TODO #5154 If the given type is `List`, `Map` or `Set`, a proxy object will be returned which
    // calls the corresponding Python methods (`__len__`, `__getitem__`, etc.). (If proxy is
    // passed back through j2p, the original Python object should be unwrapped. Maybe make proxies
    // implement an interface with a getPyObject method. PyObject could also implement this, returning
    // itself.)
    // Not sure whether to do this with java.lang.reflect.Proxy or with pre-defined classes PyList,
    // PyMap, etc. It might be easier to implement this in Java.
    public native <T> T toJava(Class<T> klass);

    /** Equivalent to Python `id()`. */
    public native long id();

    /** Equivalent to Python `type()`. */
    public native PyObject type();

    /** Equivalent to Python `()` syntax. Keyword arguments may be passed using instances of {@link
     * Kwarg} at the end of the parameter list. Parameters will be converted as described at
     * {@link #fromJava fromJava()}. */
    public native PyObject call(Object... args);

    /** Equivalent to `{@link #get get}(key).{@link #call call}(args)`, except it throws a
     * PyException if the attribute does not exist. */
    public PyObject callAttr(String key, Object... args) {
        PyObject value = get(key);
        if (value == null) {
            throw new PyException("AttributeError: object has no attribute '" + key + "'");
        }
        return value.call(args);
    }

    // ==== Map ==============================================================

    /** Attempts to remove all attributes returned by `dir()`. Because `dir()` usually returns
     * non-removable attributes such as `__class__`, this will probably fail unless
     * the object has a custom `__dir__` method.
     *
     * See also the notes on {@link #remove remove()} and {{@link #isEmpty}. */
    @Override public void clear() { super.clear(); }

    /** Equivalent to `{@link #keySet()}.isEmpty()`. Because `dir()` usually returns an object's
     * class attributes, `isEmpty` is unlikely ever to return true (even after calling {@link
     * #clear}), unless the object has a custom `__dir__` method. */
    @Override public boolean isEmpty() { return super.isEmpty(); }

    /** Equivalent to Python `hasattr()`. */
    @Override public native boolean containsKey(Object key);

    /** The value will be converted as described at {@link #fromJava fromJava()}.*/
    // Need override because the AbstractMap implementation calls equals() on the given value, not
    // the values in the map.
    @Override public boolean containsValue(Object o) {
        for (Entry<String,PyObject> entry : entrySet()) {
            PyObject value = entry.getValue();
            if ((o == null && value == null) || value.equals(o)) {
                return true;
            }
        }
        return false;
    }

    /** Equivalent to Python `getattr()`. */
    @Override public native PyObject get(Object key);

    /** Equivalent to Python `setattr()`. */
    @Override public PyObject put(String key, PyObject value) { return put(key, (Object)value); }

    /** Equivalent to Python `setattr()`. The value will be converted as described at
     * {@link #fromJava fromJava()}.*/
    public native PyObject put(String key, Object value);

    /** Equivalent to Python `delattr()`. This usually means it will only succeed in removing
     * attributes of the object itself, even though `dir()` also returns an object's class attributes
     * by default, */
    @Override public native PyObject remove(Object key);

    /** Equivalent to Python `dir()`. The returned set is backed by the Python object, so changes to
     * the object are reflected in the set, and vice-versa. If the object is modified while an
     * iteration over the set is in progress (except through the iterator's own `remove` operation),
     * the results of the iteration are undefined. The set supports element removal, but see the
     * notes on {@link #remove remove()}. It does not support the `add` or `addAll` operations. */
    @Override public Set<String> keySet() { return super.keySet(); }

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

    /** Equivalent to Python `==` operator.
     * @param that Object to compare with this object. It will be converted as described at
     * {@link #fromJava fromJava()}.
     * @return `true` if the given object is equal to this object. */
    @Override public native boolean equals(Object that);

    /** Equivalent to Python `str()`.
     * @return A string representation of the object. */
    @Override public native String toString();

    /** Equivalent to Python `repr()`. */
    public native String repr();

    /** Equivalent to Python `hash()`.
     * @return The hash code value for this object. */
    @Override public native int hashCode();

    /** Calls {@link #close}. */
    @Override
    protected void finalize() throws Throwable {
        close();
        super.finalize();
    }
}
