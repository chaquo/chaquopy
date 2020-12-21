package com.chaquo.python;

import java.lang.ref.*;
import java.lang.reflect.*;
import java.util.*;
import org.jetbrains.annotations.*;

/** <p>Interface to a Python object.</p>
 *
 * <ul>
 * <li>Python {@code None} is represented by Java {@code null}. Other PyObjects can be
 * converted to their Java equivalents using {@link #toJava toJava()}.</li>
 *
 * <li>If a Python object is retrieved for which a PyObject already exists, the same
 * PyObject will be returned.</li>
 * </ul>
 *
 * <p>Unless otherwise specified, all methods in this class throw {@link PyException} on
 * failure.</p> */
@SuppressWarnings({"deprecation", "DeprecatedIsStillUsed"})
public class PyObject extends AbstractMap<String,PyObject> implements AutoCloseable {
    private static final Map<Long, WeakReference<PyObject>> cache = new HashMap<>();

    /** @deprecated Internal use in conversion.pxi */
    public long addr;

    /** @deprecated Internal use in conversion.pxi */
    public static PyObject getInstance(long addr) {
        if (addr == 0) return null;
        synchronized (cache) {
            WeakReference<PyObject> wr = cache.get(addr);
            if (wr != null) {
                // wr.get() will return null if the PyObject is unreachable but it has not yet
                // been removed from the cache. In that case, the constructor call below will
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
    }

    /** <p>Releases the reference to the Python object. Unless the object represents an
     * expensive resource, there's no need to call this method: it will be called
     * automatically when the PyObject is garbage-collected.</p>
     *
     * <p>After calling {@code close}, the PyObject can no longer be used. If there are no
     * other references to the underlying object, it may be destroyed by Python. If it
     * continues to exist and is retrieved by Java code again, a new PyObject will be
     * returned.</p>
     *
     * <p>Caution: any references to the same Python object elsewhere in your program will be
     * represented by the same PyObject, so they will all be invalidated by this call.</p> */
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

    /** <p>Converts the given Java object to a Python object. There's usually no need to call
     * this method: it will be called automatically by the methods of this class which take
     * {@code Object} parameters.</p>
     *
     * <p>For details of how Java objects are represented in Python, see the
     * <a href="../../../../python.html#data-types-overview">Python API</a>.</p> */
    public static PyObject fromJava(Object o) {
        return getInstance(fromJavaNative(o));
    }
    private static native long fromJavaNative(Object o);

    /** <p>Converts the Python object to the given Java type.</p>
     *
     * <p>If {@code klass} is a primitive type such as {@code int}, or an immutable value type
     * such as {@code Integer} or {@code String}, and the Python object is compatible with it,
     * an equivalent Java object will be returned. However, it's more efficient to use the
     * specific methods like {@link #toInt}, {@link #toString}, etc.</p>
     *
     * <p>If {@code klass} is an array type, and the Python object is a <a
     * href="https://docs.python.org/3/glossary.html#term-sequence">sequence</a>, then a copy
     * of the sequence will be returned as a new array. In general, each element will be
     * converted as if {@code toJava} was called on it recursively. However, when converting a
     * Python {@code bytes} or {@code bytearray} object to a Java {@code byte[]} array, there
     * is an unsigned-to-signed conversion: Python values 128 to 255 will be mapped to Java
     * values -128 to -1.</p>
     *
     * <p>If the Python object is a <a href="../../../../python.html#java.jclass">jclass</a> or
     * <a href="../../../../python.html#java.jarray">jarray</a> object which is compatible with
     * {@code klass}, the underlying Java object will be returned.</p>
     *
     * <p>Otherwise, a {@code ClassCastException} will be thrown.</p> */
    public native @NotNull <T> T toJava(@NotNull Class<T> klass);


    // === Primitive conversions =============================================

    /** Converts a Python {@code bool} to a Java {@code boolean}.
     * @throws ClassCastException if the Python object is not compatible */
    public native boolean toBoolean();

    /** Converts a Python {@code int} to a Java {@code byte}.
     * @throws ClassCastException if the Python object is not compatible */
    public native byte toByte();

    /** Converts a 1-character Python string to a Java {@code char}.
     * @throws ClassCastException if the Python object is not compatible */
    public native char toChar();

    /** Converts a Python {@code int} to a Java {@code short}.
     * @throws ClassCastException if the Python object is not compatible */
    public native short toShort();

    /** Converts a Python {@code int} to a Java {@code int}.
     * @throws ClassCastException if the Python object is not compatible */
    public native int toInt();

    /** Converts a Python {@code int} to a Java {@code long}.
     * @throws ClassCastException if the Python object is not compatible */
    public native long toLong();

    /** Converts a Python {@code float} or {@code int}  to a Java {@code float}.
     * @throws ClassCastException if the Python object is not compatible */
    public native float toFloat();

    /** Converts a Python {@code float} or {@code int} to a Java {@code double}.
     * @throws ClassCastException if the Python object is not compatible */
    public native double toDouble();


    // === Container views ===================================================

    /** <p>Returns a view of the Python object as a list. The view is backed by the object, so
     * changes to the object are reflected in the view, and vice-versa.</p>
     *
     * <p>To add Java objects to the Python container through the view, first convert them
     * using {@link #fromJava fromJava()}.</p>
     *
     * @throws UnsupportedOperationException if the Python object does not implement the
     * methods {@code __getitem__} and {@code __len__}. */
    public @NotNull List<PyObject> asList() { return new PyList(this); }

    /** <p>Returns a view of the Python object as a map. The view is backed by the object, so
     * changes to the object are reflected in the view, and vice-versa.</p>
     *
     * <p>PyObject already implements the {@code Map} interface, but that is for attribute
     * access (Python "{@code .}" syntax), whereas the {@code Map} returned by this method is
     * for container access (Python "{@code []}" syntax).</p>
     *
     * <p>To add Java objects to the Python container through the view, first convert them
     * using {@link #fromJava fromJava()}.</p>
     *
     * @throws UnsupportedOperationException if the Python object does not implement the
     * methods {@code __contains__}, {@code __getitem__}, {@code __iter__} and {@code __len__}. */
    public @NotNull Map<PyObject, PyObject> asMap() { return new PyMap(this); }

    /** <p>Returns a view of the Python object as a set. The view is backed by the object, so
     * changes to the object are reflected in the view, and vice-versa.</p>
     *
     * <p>To add Java objects to the Python container through the view, first convert them
     * using {@link #fromJava fromJava()}.</p>
     *
     * @throws UnsupportedOperationException if the Python object does not implement the
     * methods {@code __contains__}, {@code __iter__} and {@code __len__}. */
    public @NotNull Set<PyObject> asSet() { return new PySet(this); }


    // === Miscellaneous =====================================================

    /** Equivalent to Python {@code id()}. */
    public native long id();

    /** Equivalent to Python {@code type()}. */
    public @NotNull PyObject type() {
        return getInstance(typeNative());
    }
    private native long typeNative();

    /** Equivalent to Python {@code ()} syntax. Arguments will be converted as described at
     * {@link #fromJava fromJava()}. Keyword arguments can be passed using instances of {@link
     * Kwarg} at the end of the argument list. */
    public PyObject call(Object... args) {
        try {
            return callThrows(args);
        } catch (PyException e) {
            throw e;
        } catch (Throwable e) {
            throw new PyException(e);
        }
    }

    /** Same as {@link #call call()}, except it directly passes any Java exception thrown
     * by the Python code. */
    public PyObject callThrows(Object... args) throws Throwable {
        return getInstance(callThrowsNative(args));
    }
    private native long callThrowsNative(Object... args) throws Throwable;

    /** Same as {@link #get get}{@code (key).}{@link #call call}{@code (args)}, except it
     * throws a {@link PyException} if the attribute does not exist. */
    public PyObject callAttr(@NotNull String key, Object... args) {
        try {
            return callAttrThrows(key, args);
        } catch (PyException e) {
            throw e;
        } catch (Throwable e) {
            throw new PyException(e);
        }
    }

    /** Same as {@link #callAttr callAttr()}, except it directly passes any Java exception
     * thrown by the Python code. */
    public PyObject callAttrThrows(@NotNull String key, Object... args) throws Throwable {
        return getInstance(callAttrThrowsNative(key, args));
    }
    private native long callAttrThrowsNative(String key, Object... args) throws Throwable;

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

    /** <p>Attempts to remove all attributes returned by {@link #keySet()}. See notes on
     * {@link #isEmpty}.</p> */
    @Override public void clear() { super.clear(); }

    /** Equivalent to {@link #keySet()}{@code .isEmpty()}. Because {@code keySet} usually
     * includes the object's class attributes, {@code isEmpty} will never return true even
     * after calling {@link #clear}, unless the object has a custom {@code __dir__} method. */
    @Override public boolean isEmpty() { return super.isEmpty(); }

    /** Equivalent to Python {@code hasattr()}. */
    @Override public boolean containsKey(@NotNull Object key) {
        return containsKeyNative((String)key);
    }
    private native boolean containsKeyNative(String key);

    /** Returns whether any attribute has the given value. The value will be converted as
     * described at {@link #fromJava fromJava()}. */
    @Override public boolean containsValue(Object o) {
        return super.containsValue(fromJava(o));
    }

    /** Equivalent to Python {@code getattr()}. In accordance with the {@code Map} interface,
     * when the attribute does not exist, this method returns {@code null} rather than
     * throwing an exception. To distinguish this from an attribute with a value of {@code
     * None}, use {@link #containsKey containsKey()}. */
    @Override public PyObject get(@NotNull Object key) {
        return getInstance(getNative((String)key));
    }
    private native long getNative(String key);

    /** Equivalent to Python {@code setattr()}. */
    @Override public PyObject put(@NotNull String key, PyObject value) {
        return put(key, (Object)value);
    }

    /** Equivalent to Python {@code setattr()}. The value will be converted as described at
     * {@link #fromJava fromJava()}.*/
    public PyObject put(@NotNull String key, Object value) {
        return getInstance(putNative(key, value));
    }
    private native long putNative(String key, Object value);

    /** <p>Equivalent to Python {@code delattr()}. This means it can only remove attributes of
     * the object itself, even though {@link #keySet()} usually includes the object's class
     * attributes as well.</p>
     *
     * <p>In accordance with the {@code Map} interface, when the attribute does not exist, this
     * method returns {@code null} rather than throwing an exception.</p> */
    @Override public PyObject remove(@NotNull Object key) {
        return getInstance(removeNative((String)key));
    }
    private native long removeNative(String key);

    /** <p>Equivalent to Python {@code dir()}. Unless the object has a custom {@code __dir__}
     * method, this means the result will include attributes from the object's class as well
     * as the object itself.</p>
     *
     * <p>The returned set is backed by the Python object, so changes to the object are
     * reflected in the set, and vice-versa. If the object is modified while an iteration over
     * the set is in progress (except through the iterator's own {@code remove} operation), the
     * results of the iteration are undefined. The set supports element removal, but see the
     * notes on {@link #remove remove()}. It does not support the {@code add} or {@code addAll}
     * operations.</p> */
    @Override public @NotNull Set<String> keySet() { return super.keySet(); }

    /** See notes on {@link #keySet()}. */
    @Override public @NotNull Set<Entry<String, PyObject>> entrySet() {
        return new AbstractSet<Entry<String, PyObject>>() {
            @Override public int size() { return dir().size(); }

            @Override public @NotNull Iterator<Entry<String, PyObject>> iterator() {
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

    /** Equivalent to Python {@code ==} operator. The given object will be converted as
     * described at {@link #fromJava fromJava()} */
    @Override public native boolean equals(Object that);

    /** Equivalent to Python {@code str()}. */
    @Override public native @NotNull String toString();

    /** Equivalent to Python {@code repr()}. */
    public native @NotNull String repr();

    /** Equivalent to Python {@code hash()}. */
    @Override public native int hashCode();

    /** Calls {@link #close}. */
    @Override protected void finalize() throws Throwable {
        close();
        super.finalize();
    }
}
