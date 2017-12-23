package com.chaquo.python;

import java.lang.ref.*;
import java.lang.reflect.*;
import java.util.*;


/** Interface to a Python object.
 *
 * * Python `None` is represented by Java `null`. Other `PyObject`s can be converted to their Java
 *   equivalents using {@link #toJava toJava()}.
 * * If a Python object is retrieved for which a PyObject already exists, the same PyObject will be
 *   returned.
 *
 * Unless otherwise specified, all methods in this class throw {@link PyException} on failure.*/
@SuppressWarnings({"deprecation", "DeprecatedIsStillUsed"})
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
     * and is retrieved by Java code again, a new PyObject will be returned. */
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
     * * Otherwise, a Python <a href="../../../../python.html#java.jclass">jclass</a> or
     *   <a href="../../../../python.html#java.jarray">jarray</a> object will be created. */
    //
    // TODO #5154... If the given object implements `List`, `Map` or `Set`, the proxy object will
    // implement the corresponding Python methods (`__len__`, `__getitem__`, etc.).
    public static native PyObject fromJava(Object o);

    /** Attempts to view the Python object as the given Java type. For example.
     * `toJava(String.class)` will attempt to view the object as a String.
     *
     * * If the given type is an immutable value type such as `Boolean`, `Integer` or `String`,
     *   and the Python object is of a compatible type, an equivalent object will be returned.
     * * If the Python object is itself a proxy for a Java object of a compatible type, the
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
    public PyObject call(Object... args) {
        try {
            return callThrows(args);
        } catch (PyException e) {
            throw e;
        } catch (Throwable e) {
            throw new PyException(e);
        }
    }

    /** Same as {@link #call call()}, except that it directly passes any Java exception thrown by
     * the Python code rather than wrapping it in a PyException */
    public native PyObject callThrows(Object... args) throws Throwable;


    /** Equivalent to `{@link #get get}(key).{@link #call call}(args)`, except it throws a
     * PyException if the attribute does not exist. */
    public PyObject callAttr(String key, Object... args) {
        try {
            return callAttrThrows(key, args);
        } catch (PyException e) {
            throw e;
        } catch (Throwable e) {
            throw new PyException(e);
        }
    }

    /** Same as {@link #callAttr callAttr()}, except that it directly passes any Java exception
     * thrown by the Python code rather than wrapping it in a PyException */
    public native PyObject callAttrThrows(String key, Object... args) throws Throwable;

    /** @deprecated internal use in files generated by static_proxy.py */
    public static PyObject _chaquopyCall(StaticProxy sp, String name, Object... args) {
        try {
            return PyObject.fromJava(sp).callAttrThrows(name, args);
        } catch (RuntimeException | Error e) {
            throw e;
        } catch (Throwable e) {
            throw new UndeclaredThrowableException(e);
        }
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

    /** Equivalent to Python `getattr()`. In accordance with the `Map` interface, when the attribute
     * does not exist, this method returns `null` rather than throwing an exception. To distinguish
     * this from an attribute with a value of `None`, use {@link #containsKey containsKey()}. */
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
