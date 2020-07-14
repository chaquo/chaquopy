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

    /** @deprecated Internal use in chaquopy_java.pyx. */
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
            PyObject po = new PyObject(addr);
            cache.put(addr, new WeakReference<>(po));
            return po;
        }
    }

    private PyObject(long addr) {
        this.addr = addr;
        openNative();
    }
    private native void openNative();


    /** Releases the reference to the Python object. Unless the object represents an expensive
     * resource, there's no need to call this method directly: it will be called automatically
     * when the PyObject is garbage-collected.
     *
     * After calling `close()`, the PyObject can no longer be used. If there are no other
     * references to the underlying object, it may be destroyed by Python. If it continues to exist
     * and is retrieved by Java code again, a new PyObject will be returned.
     *
     * Caution: any references to the same Python object elsewhere in your program will be
     * represented by the same PyObject, so they will all be invalidated by this call. */
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
     * There's usually no need to call this method directly: it will be called automatically by the
     * methods of this class which take `Object` parameters.
     *
     * For details of how Java objects are represented in Python, see the
     * <a href="../../../../python.html#data-types-overview">Python API</a>. */
    public static native PyObject fromJava(Object o);

    /** Converts the Python object to the given Java type.
     *
     * If `klass` is a primitive type (such as `int`), or an immutable value type (such as
     * `Integer` or `String`), and the Python object is compatible with it, an equivalent Java
     * object will be returned. However, it's more readable to use the type-specific methods
     * like {@link #toInt}, {@link #toString}, etc.
     *
     * If `klass` is an array type, and the Python object is a <a
     * href="https://docs.python.org/3/glossary.html#term-sequence">sequence</a>, then a copy
     * of the sequence will be returned as a new array. In general, each element will be
     * converted as if `toJava` was called on it recursively. However, when converting a Python
     * `bytes` or `bytearray` object to a Java `byte[]` array, there is an
     * unsigned-to-signed conversion: Python values 128 to 255 will be mapped to Java values
     * -128 to -1.
     *
     * If the Python object is a <a href="../../../../python.html#java.jclass">jclass</a> or <a
     * href="../../../../python.html#java.jarray">jarray</a> object which is compatible with
     * `klass`, the underlying Java object will be returned.
     *
     * Otherwise, a `ClassCastException` will be thrown. */
    public native <T> T toJava(Class<T> klass);


    // === Primitive conversions =============================================

    /** Converts a Python `bool` to a Java `boolean`.
     * @throws ClassCastException if the Python object is not of a compatible type */
    public boolean toBoolean() { return toJava(boolean.class); }

    /** Converts a Python `int` to a Java `byte`.
     * @throws ClassCastException if the Python object is not of a compatible type */
    public byte toByte() { return toJava(byte.class); }

    /** Converts a 1-character Python string to a Java `char`.
     * @throws ClassCastException if the Python object is not of a compatible type */
    public char toChar() { return toJava(char.class); }

    /** Converts a Python `int` to a Java `short`.
     * @throws ClassCastException if the Python object is not of a compatible type */
    public short toShort() { return toJava(short.class); }

    /** Converts a Python `int` to a Java `int`.
     * @throws ClassCastException if the Python object is not of a compatible type */
    public int toInt() { return toJava(int.class); }

    /** Converts a Python `int` to a Java `long`.
     * @throws ClassCastException if the Python object is not of a compatible type */
    public long toLong() { return toJava(long.class); }

    /** Converts a Python `float` or `int`  to a Java `float`.
     * @throws ClassCastException if the Python object is not of a compatible type */
    public float toFloat() { return toJava(float.class); }

    /** Converts a Python `float` or `int` to a Java `double`.
     * @throws ClassCastException if the Python object is not of a compatible type */
    public double toDouble() { return toJava(double.class); }


    // === Container views ===================================================

    /** Returns a view of the Python object as a list. The view is backed by the object, so
     * changes to the object are reflected in the view, and vice-versa.
     *
     * To add Java objects to the Python container through the view, first convert them using
     * {@link #fromJava fromJava}.
     *
     * @throws UnsupportedOperationException if the Python object does not implement the
     * methods `__getitem__` and `__len__`. */
    public List<PyObject> asList() { return new PyList(this); }

    /** Returns a view of the Python object as a map. The view is backed by the object, so
     * changes to the object are reflected in the view, and vice-versa.
     *
     * PyObject already implements the `Map` interface, but that is for attribute access
     * (Python "`.`" syntax), whereas the `Map` returned by this method is for container access
     * (Python "`[]`" syntax).
     *
     * To add Java objects to the Python container through the view, first convert them using
     * {@link #fromJava fromJava}.
     *
     * @throws UnsupportedOperationException if the Python object does not implement the
     * methods `__contains__`, `__getitem__`, `__iter__` and `__len__`. */
    public Map<PyObject, PyObject> asMap() { return new PyMap(this); }

    /** Returns a view of the Python object as a set. The view is backed by the object, so
     * changes to the object are reflected in the view, and vice-versa.
     *
     * To add Java objects to the Python container through the view, first convert them using
     * {@link #fromJava fromJava}.
     *
     * @throws UnsupportedOperationException if the Python object does not implement the
     * methods `__contains__`, `__iter__` and `__len__`. */
    public Set<PyObject> asSet() { return new PySet(this); }


    // === Miscellaneous =====================================================

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


    // ==== Attributes =======================================================

    /** Removes all attributes returned by `dir()`. Because `dir()` usually includes
     * non-removable attributes such as `__class__`, this will probably fail unless
     * the object has a custom `__dir__` method.
     *
     * See also the notes on {@link #remove remove()} and {@link #isEmpty}. */
    @Override public void clear() { super.clear(); }

    /** Equivalent to `{@link #keySet()}.isEmpty()`. Because `dir()` usually includes an object's
     * class attributes, `isEmpty` is unlikely ever to return true, even after calling {@link
     * #clear}, unless the object has a custom `__dir__` method. */
    @Override public boolean isEmpty() { return super.isEmpty(); }

    /** Equivalent to Python `hasattr()`. */
    @Override public native boolean containsKey(Object key);

    /** The value will be converted as described at {@link #fromJava fromJava()}.*/
    @Override public boolean containsValue(Object o) {
        return super.containsValue(fromJava(o));
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
     * by default
     *
     * In accordance with the `Map` interface, when the attribute does not exist, this method
     * returns `null` rather than throwing an exception. */
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


    // === Object methods ====================================================

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
