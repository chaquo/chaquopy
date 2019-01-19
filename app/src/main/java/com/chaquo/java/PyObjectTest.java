package com.chaquo.java;

import com.chaquo.python.*;
import java.io.*;
import java.util.*;
import org.junit.*;
import org.junit.rules.*;
import org.junit.runners.*;

import static org.hamcrest.CoreMatchers.containsString;
import static org.hamcrest.core.AnyOf.anyOf;
import static org.hamcrest.core.IsEqual.equalTo;
import static org.hamcrest.core.IsInstanceOf.any;
import static org.hamcrest.core.IsNull.nullValue;
import static org.junit.Assert.*;


@FixMethodOrder(MethodSorters.NAME_ASCENDING)
public class PyObjectTest {
    @Rule
    public ExpectedException thrown = ExpectedException.none();

    private Python python;
    private PyObject builtins;
    private PyObject pyobjecttest;

    @Before
    public void setUp() {
        python = Python.getInstance();
        builtins = python.getBuiltins();
        pyobjecttest = python.getModule("chaquopy.test.pyobjecttest");
    }

    @Test
    public void identity() {
        PyObject SO = pyobjecttest.get("SimpleObject");
        assertSame(SO, pyobjecttest.get("SimpleObject"));
        SO.close();
        assertNotSame(SO, pyobjecttest.get("SimpleObject"));
    }

    /** Check for deadlocks and other threading errors by creating, accessing and destroying large
     * numbers of PyObjects on 2 threads simultaneously. */
    @Test
    public void multithreading() {
        final long stopTime = System.currentTimeMillis() + 100;
        Runnable r = new Runnable() {
            @Override public void run() {
                Random random = new Random();
                PyObject SO = pyobjecttest.get("SimpleObject");
                while (System.currentTimeMillis() < stopTime) {
                    PyObject so = SO.call();
                    int x = random.nextInt();
                    so.put("x", x);
                    assertEquals(x, (int) so.get("x").toJava(int.class));
                    so.close();
                }
            }
        };
        Thread t = new Thread(r);
        t.start();  // Run it on the other thread.
        r.run();    // And do the same on this thread.
        try {
            t.join();
        } catch (InterruptedException e) {
            fail();
        }
    }

    @Test
    public void close() {
        PyObject DT = pyobjecttest.get("DelTrigger");
        DT.put("triggered", false);
        PyObject dt = DT.call();
        assertFalse(DT.get("triggered").toJava(Boolean.class));
        dt.close();
        assertTrue(DT.get("triggered").toJava(Boolean.class));

        thrown.expect(PyException.class);
        thrown.expectMessage("ValueError");
        thrown.expectMessage("closed");
        dt.id();
    }

    @SuppressWarnings("AssertEqualsBetweenInconvertibleTypes")
    @Test
    public void fromJava() {
        assertEquals(PyObject.fromJava(null), null);
        assertEquals(PyObject.fromJava(true), true);
        assertEquals(PyObject.fromJava(42), 42);
        assertEquals(PyObject.fromJava("hello"), "hello");

        Thread t = Thread.currentThread();
        assertEquals(PyObject.fromJava(t).callAttr("getName"),
                     t.getName());
    }

    @Test
    public void toJava() {
        PyObject z = pyobjecttest.get("bool_var");
        assertEquals(true, z.toJava(Boolean.class));
        assertEquals(true, z.toJava(boolean.class));

        PyObject i = pyobjecttest.get("int_var");
        assertEquals(42, (int) i.toJava(Integer.class));
        assertEquals(42, (int) i.toJava(int.class));
        assertEquals(42.0, i.toJava(Double.class), 0.0001);
        assertEquals(42.0, i.toJava(double.class), 0.0001);
        assertEquals(42L, i.toJava(Number.class));    // new Long(42).equals(new Integer(42)) == false!
        assertEquals(42L, i.toJava(Object.class));    //

        PyObject f = pyobjecttest.get("float_var");
        assertEquals(43.5, f.toJava(Double.class), 0.0001);
        assertEquals(43.5, f.toJava(double.class), 0.0001);
        assertEquals(43.5, f.toJava(Float.class), 0.0001);
        assertEquals(43.5, f.toJava(float.class), 0.0001);
        assertEquals(43.5, f.toJava(Number.class));

        assertEquals("hello", pyobjecttest.get("str_var").toJava(String.class));
        assertEquals("x", pyobjecttest.get("char_var").toJava(String.class));
        assertEquals('x', (char) pyobjecttest.get("char_var").toJava(Character.class));
        assertEquals('x', (char) pyobjecttest.get("char_var").toJava(char.class));

        assertSame(pyobjecttest, pyobjecttest.toJava(PyObject.class));

        Thread t = Thread.currentThread();
        assertSame(t, PyObject.fromJava(t).toJava(Thread.class));
    }

    @Test
    public void toJava_fail_void() {
        thrown.expect(ClassCastException.class);
        thrown.expectMessage("Cannot convert float object to void");
        pyobjecttest.get("float_var").toJava(void.class);
    }

    @Test
    public void toJava_fail_Void() {
        thrown.expect(ClassCastException.class);
        thrown.expectMessage("Cannot convert float object to java.lang.Void");
        pyobjecttest.get("float_var").toJava(Void.class);
    }

    @Test
    public void toJava_fail_float_to_int() {
        thrown.expect(ClassCastException.class);
        thrown.expectMessage("Cannot convert float object to java.lang.Integer");
        pyobjecttest.get("float_var").toJava(int.class);
    }

    @Test
    public void toJava_fail_string_to_int() {
        thrown.expect(ClassCastException.class);
        thrown.expectMessage("Cannot convert str object to java.lang.Integer");
        pyobjecttest.get("str_var").toJava(Integer.class);
    }

    @Test
    public void toJava_fail_int_to_string() {
        thrown.expect(ClassCastException.class);
        thrown.expectMessage("Cannot convert int object to java.lang.String");
        pyobjecttest.get("int_var").toJava(String.class);
    }

    @Test
    public void toBoolean() {
        assertTrue(pyobjecttest.get("bool_var").toBoolean());

        thrown.expect(ClassCastException.class);
        thrown.expectMessage("Cannot convert int object to java.lang.Boolean");
        pyobjecttest.get("int_var").toBoolean();
    }

    @Test
    public void toByte() {
        assertEquals(42, pyobjecttest.get("int_var").toByte());
        assertEquals(-42, pyobjecttest.get("negative_int_var").toByte());

        thrown.expect(ClassCastException.class);
        thrown.expectMessage("Cannot convert float object to java.lang.Byte");
        pyobjecttest.get("float_var").toByte();
    }

    @Test
    public void toByte_overflow() {
        thrown.expect(PyException.class);
        thrown.expectMessage("too large");
        pyobjecttest.get("short_int_var").toByte();
    }

    @Test
    public void toChar() {
        assertEquals('x', pyobjecttest.get("char_var").toChar());

        thrown.expect(ClassCastException.class);
        thrown.expectMessage("Cannot convert int object to java.lang.Character");
        pyobjecttest.get("int_var").toChar();
    }

    @Test
    public void toChar_length() {
        thrown.expect(PyException.class);
        thrown.expectMessage("only single character unicode strings can be converted");
        pyobjecttest.get("str_var").toChar();
    }

    @Test
    public void toShort() {
        assertEquals(1234, pyobjecttest.get("short_int_var").toShort());

        thrown.expect(ClassCastException.class);
        thrown.expectMessage("Cannot convert bool object to java.lang.Short");
        pyobjecttest.get("bool_var").toShort();
    }

    @Test
    public void toShort_overflow() {
        thrown.expect(PyException.class);
        thrown.expectMessage("too large");
        pyobjecttest.get("medium_int_var").toShort();
    }


    @Test
    public void toInt() {
        assertEquals(123456, pyobjecttest.get("medium_int_var").toInt());

        thrown.expect(ClassCastException.class);
        thrown.expectMessage("Cannot convert str object to java.lang.Int");
        pyobjecttest.get("str_var").toInt();
    }

    @Test
    public void toInt_overflow() {
        thrown.expect(PyException.class);
        thrown.expectMessage("too large");
        pyobjecttest.get("long_int_var").toInt();
    }

    @Test
    public void toLong() {
        assertEquals(123456, pyobjecttest.get("medium_int_var").toLong());
        assertEquals(9876543210L, pyobjecttest.get("long_int_var").toLong());

        thrown.expect(ClassCastException.class);
        thrown.expectMessage("Cannot convert list object to java.lang.Long");
        pyobjecttest.get("list_var").toLong();
    }

    @Test
    public void toLong_overflow() {
        thrown.expect(PyException.class);
        thrown.expectMessage(anyOf(containsString("too large"),  // 64-bit Linux/Android
                                   containsString("too big")));  // Other platforms
        pyobjecttest.get("super_long_int_var").toLong();
    }

    @Test
    public void toFloat() {
        assertEquals(42.0, pyobjecttest.get("int_var").toFloat(), 1e-5);
        assertEquals(9.87654e9, pyobjecttest.get("long_int_var").toFloat(), 0.00001e9);
        assertEquals(9.87654e18, pyobjecttest.get("super_long_int_var").toFloat(), 0.00001e18);
        assertEquals(43.5, pyobjecttest.get("float_var").toFloat(), 1e-5);

        thrown.expect(ClassCastException.class);
        thrown.expectMessage("Cannot convert str object to java.lang.Float");
        pyobjecttest.get("char_var").toFloat();
    }

    @Test
    public void toFloat_overflow() {
        thrown.expect(PyException.class);
        thrown.expectMessage("too large");
        pyobjecttest.get("double_var").toFloat();
    }

    @Test
    public void toDouble() {
        assertEquals(42.0, pyobjecttest.get("int_var").toDouble(), 1e-13);
        assertEquals(9.87654e9, pyobjecttest.get("long_int_var").toDouble(), 0.00001e9);
        assertEquals(9.87654e18, pyobjecttest.get("super_long_int_var").toDouble(), 0.00001e18);
        assertEquals(43.5, pyobjecttest.get("float_var").toDouble(), 1e-13);
        assertEquals(1e39, pyobjecttest.get("double_var").toDouble(), 1e24);

        thrown.expect(ClassCastException.class);
        thrown.expectMessage("Cannot convert bool object to java.lang.Double");
        pyobjecttest.get("bool_var").toDouble();
    }

    @SuppressWarnings("AssertEqualsBetweenInconvertibleTypes")
    @Test
    public void id() {
        PyObject True = builtins.get("True"), False = builtins.get("False");
        assertNotSame(True, False);
        assertNotEquals(True.id(), False.id());
        assertEquals(True.id(), (long)builtins.callAttr("id", True).toJava(Long.class));
    }

    @Test
    public void type() {
        PyObject True = builtins.get("True"), False = builtins.get("False");
        PyObject bool = builtins.get("bool"), type = builtins.get("type");
        assertSame(True.type(), False.type());
        assertSame(bool, True.type());
        assertSame(type, bool.type());
        assertSame(type, type.type());
        assertNotSame(type, bool);
    }

    // javac still uses Latin-1 by default when reading source files, or when printing any errors
    // which occur during these tests.
    private static String exceptionMsg = "abc ol\u00e9 \u4e2d\u6587";

    @Test
    public void call() {
        PyObject sm = pyobjecttest.get("sum_mul");
        assertEquals(0,  (int)sm.call().toJava(Integer.class));
        assertEquals(3,  (int)sm.call(3).toJava(Integer.class));
        assertEquals(6,  (int)sm.call(1, 2, 3).toJava(Integer.class));
        assertEquals(24, (int)sm.call(6, new Kwarg("mul", 4)).toJava(Integer.class));
        assertEquals(2,  (int)sm.call(1, 2, 3, new Kwarg("div", 3)).toJava(Integer.class));
        assertEquals(10, (int)sm.call(1, 2, 3, new Kwarg("mul", 5),
                                      new Kwarg("div", 3)).toJava(Integer.class));

        PyObject two = sm.call(2), three = sm.call(3), four = sm.call(4);
        assertEquals(14, (int)sm.call(three, four, new Kwarg("mul", two)).toJava(Integer.class));

        thrown.expect(PyException.class);
        thrown.expectMessage(equalTo("java.io.IOException: " + exceptionMsg));
        thrown.expectCause(any(IOException.class));
        // Stack trace merging is covered in test_proxy.py.
        pyobjecttest.get("throws_java").call();
    }

    @Test
    public void callThrows() throws Throwable {
        thrown.expect(IOException.class);
        thrown.expectMessage(equalTo(exceptionMsg));
        thrown.expectCause(nullValue(Throwable.class));
        pyobjecttest.get("throws_java").callThrows();
    }

    @Test
    public void callAttr() {
        assertEquals(0,  (int)pyobjecttest.callAttr("sum_mul").toJava(Integer.class));
        assertEquals(3,  (int)pyobjecttest.callAttr("sum_mul", 3).toJava(Integer.class));
        assertEquals(6,  (int)pyobjecttest.callAttr("sum_mul", 1, 2, 3).toJava(Integer.class));
        assertEquals(24, (int)pyobjecttest.callAttr("sum_mul", 6, new Kwarg("mul", 4)).toJava(Integer.class));

        thrown.expect(PyException.class);
        thrown.expectMessage(equalTo("java.io.IOException: " + exceptionMsg));
        thrown.expectCause(any(IOException.class));
        pyobjecttest.callAttr("throws_java");
    }

    @Test
    public void callAttrThrows() throws Throwable {
        thrown.expect(IOException.class);
        thrown.expectMessage(equalTo(exceptionMsg));
        thrown.expectCause(nullValue(Throwable.class));
        pyobjecttest.callAttrThrows("throws_java");
    }

    @Test
    public void callAttrThrowsPython() throws Throwable {
        thrown.expect(PyException.class);
        thrown.expectMessage(equalTo("ValueError: " + exceptionMsg));
        thrown.expectCause(nullValue(Throwable.class));
        pyobjecttest.callAttrThrows("throws_python");
    }

    @Test
    public void callAttr_fail_nonexistent() {
        thrown.expect(PyException.class);
        thrown.expectMessage("AttributeError");
        thrown.expectMessage("has no attribute 'nonexistent'");
        pyobjecttest.callAttr("nonexistent");
    }

    @Test
    public void call_fail_count() {
        thrown.expect(PyException.class);
        thrown.expectMessage("TypeError");
        thrown.expectMessage("got 3");
        builtins.get("sum").call(1, 2, 3);
    }

    @Test
    public void call_fail_type() {
        thrown.expect(PyException.class);
        thrown.expectMessage("TypeError");
        thrown.expectMessage("unsupported operand");
        pyobjecttest.get("sum_mul").call("hello");
    }

    @Test
    public void call_fail_kwarg_duplicate() {
        thrown.expect(PyException.class);
        thrown.expectMessage("SyntaxError");
        thrown.expectMessage("repeated");
        pyobjecttest.get("sum_mul").call(6, new Kwarg("mul", 4), new Kwarg("mul", 4));
    }

    @Test
    public void call_fail_kwarg_order() {
        thrown.expect(PyException.class);
        thrown.expectMessage("SyntaxError");
        thrown.expectMessage("follows keyword");
        pyobjecttest.get("sum_mul").call(new Kwarg("mul", 4), 6);
    }

    @SuppressWarnings("AssertEqualsBetweenInconvertibleTypes")
    @Test
    public void none() {
        assertNull(builtins.get("None"));
        assertEquals(pyobjecttest.callAttr("is_none", (Object)null), true);
        assertEquals(pyobjecttest.callAttr("is_none", (Object[])null), true);  // Equivalent to an uncasted null
        assertEquals(pyobjecttest.callAttr("is_none", 42), false);
    }

    // ==== Map ==============================================================

    @Test
    public void clear() {
        PyObject so = pyobjecttest.callAttr("SimpleObject");
        assertFalse(so.isEmpty());
        so.clear();
        assertTrue(so.isEmpty());
        so.put("test", 1);
        assertFalse(so.isEmpty());
        so.clear();
        assertTrue(so.isEmpty());
    }

    @Test
    public void clear_fail_class_attribute() {
        PyObject eo = pyobjecttest.callAttr("EmptyObject");
        thrown.expect(PyException.class);
        thrown.expectMessage("can't delete __class__");
        eo.clear();
    }

    @Test
    public void containsKey() {
        PyObject so = pyobjecttest.callAttr("SimpleObject");
        assertTrue(so.containsKey("one"));
        assertFalse(so.containsKey("six"));
        assertTrue(so.containsKey("two"));
        assertFalse(so.containsKey("nine"));

        // Not returned by __dir__ override (see keySet test), but accessible anyway.
        assertTrue(so.containsKey("__class__"));
    }

    @Test
    public void containsKey_fail_null() {
        thrown.expect(PyException.class);
        thrown.expectMessage("TypeError");
        thrown.expectMessage("attribute name must be string");
        builtins.containsKey(null);
    }

    @SuppressWarnings("SuspiciousMethodCalls")
    @Test
    public void containsKey_fail_type() {
        thrown.expect(PyException.class);
        thrown.expectMessage("TypeError");
        thrown.expectMessage("attribute name must be string");
        builtins.containsKey(42);
    }

    @SuppressWarnings("SuspiciousMethodCalls")
    @Test
    public void containsValue() {
        PyObject so = pyobjecttest.callAttr("SimpleObject");
        assertTrue(so.containsValue(1));
        assertFalse(so.containsValue(6));
        assertTrue(so.containsValue(2));
        assertFalse(so.containsValue(9));
        assertFalse(so.containsValue(null));

        assertTrue(builtins.containsValue(null));   // None
        so.put("none", null);
        assertTrue(so.containsValue(null));
    }

    @SuppressWarnings({"AssertEqualsBetweenInconvertibleTypes", "ForLoopReplaceableByForEach"})
    @Test
    public void entrySet() {
        PyObject so = pyobjecttest.callAttr("SimpleObject");
        Set<Map.Entry<String,PyObject>> es = so.entrySet();

        assertEquals(3, so.size());
        assertEquals(3, es.size());
        for (Iterator<Map.Entry<String, PyObject>> iEntry = es.iterator(); iEntry.hasNext(); /**/) {
            Map.Entry<String, PyObject> entry = iEntry.next();
            String key = entry.getKey();
            PyObject value = entry.getValue();
            switch (key) {
                case "one":
                    assertEquals(value, 1);
                    break;
                case "two":
                    assertEquals(value, 2);
                    entry.setValue(PyObject.fromJava(22));
                    break;
                case "three":
                    assertEquals(value, 3);
                    iEntry.remove();
                    break;
                default:
                    fail("Unexpected key " + key);
                    break;
            }
        }

        assertEquals(2, so.size());
        assertEquals(2, es.size());
        for (Iterator<Map.Entry<String, PyObject>> iEntry = es.iterator(); iEntry.hasNext(); /**/) {
            Map.Entry<String, PyObject> entry = iEntry.next();
            String key = entry.getKey();
            PyObject value = entry.getValue();
            switch (key) {
                case "one":
                    assertEquals(value, 1);
                    break;
                case "two":
                    assertEquals(value, 22);
                    break;
                default:
                    fail("Unexpected key " + key);
                    break;
            }
        }
    }

    @SuppressWarnings("AssertEqualsBetweenInconvertibleTypes")
    @Test
    public void get() {
        assertEquals(pyobjecttest.get("nonexistent"), null);

        // This also serves as a test for equals()
        assertEquals(pyobjecttest.get("none_var"), null);
        assertEquals(pyobjecttest.get("bool_var"), true);
        assertEquals(pyobjecttest.get("int_var"), 42);
        assertEquals(pyobjecttest.get("int_var"), 42.0);
        assertEquals(pyobjecttest.get("float_var"), 43.5);
        assertEquals(pyobjecttest.get("str_var"), "hello");
    }

    @Test
    public void get_fail_null() {
        thrown.expect(PyException.class);
        thrown.expectMessage("TypeError");
        thrown.expectMessage("attribute name must be string");
        pyobjecttest.get(null);
    }

    @SuppressWarnings("SuspiciousMethodCalls")
    @Test
    public void get_fail_type() {
        thrown.expect(PyException.class);
        thrown.expectMessage("TypeError");
        thrown.expectMessage("attribute name must be string");
        pyobjecttest.get(42);
    }

    @Test
    public void isEmpty() {
        PyObject eo = pyobjecttest.callAttr("EmptyObject");
        assertFalse(eo.isEmpty());  // No __dir__ override

        PyObject so = pyobjecttest.callAttr("SimpleObject");
        assertFalse(so.isEmpty());
        so.clear();
        assertTrue(so.isEmpty());  // Has __dir__ override
    }

    @Test
    public void keySet() {
        PyObject so = pyobjecttest.callAttr("SimpleObject");
        assertEquals(new HashSet<>(Arrays.asList("one", "two", "three")),
                     so.keySet());
    }

    @SuppressWarnings("AssertEqualsBetweenInconvertibleTypes")
    @Test
    public void put() {
        PyObject so = pyobjecttest.callAttr("EmptyObject");
        assertEquals(null, so.put("a", 11));
        assertEquals(so.get("a"), 11);
        assertEquals(so.put("a", 22), 11);
        assertEquals(so.get("a"), 22);
        assertEquals(so.put("a", null), 22);
        assertEquals(so.get("a"), null);
        assertTrue(so.containsKey("a"));
    }

    @Test
    public void put_fail_null() {
        thrown.expect(PyException.class);
        thrown.expectMessage("TypeError");
        thrown.expectMessage("attribute name must be string");
        pyobjecttest.put(null, "hello");
    }

    @Test
    @SuppressWarnings("unchecked")
    public void put_fail_type() {
        thrown.expect(ClassCastException.class);
        ((Map)pyobjecttest).put(11, "hello");
    }

    @SuppressWarnings("AssertEqualsBetweenInconvertibleTypes")
    @Test
    public void remove() {
        PyObject so = pyobjecttest.callAttr("SimpleObject");
        assertTrue(so.containsKey("one"));
        assertEquals(so.remove("one"), 1);
        assertFalse(so.containsKey("one"));
        assertEquals(so.remove("one"), null);
    }

    @Test
    public void remove_fail_null() {
        thrown.expect(PyException.class);
        thrown.expectMessage("TypeError");
        thrown.expectMessage("attribute name must be string");
        pyobjecttest.remove(null);
    }

    @SuppressWarnings("SuspiciousMethodCalls")
    @Test
    public void remove_fail_type() {
        thrown.expect(PyException.class);
        thrown.expectMessage("TypeError");
        thrown.expectMessage("attribute name must be string");
        pyobjecttest.remove(42);
    }

    @Test
    public void size() {
        assertEquals(3, pyobjecttest.callAttr("SimpleObject").size());
        assertTrue(builtins.size() > 100);
        assertTrue(builtins.size() < 200);
    }

    // ==== Object ===========================================================
    
    @SuppressWarnings("AssertEqualsBetweenInconvertibleTypes")
    @Test
    public void equals() {
        PyObject True = builtins.get("True"), False = builtins.get("False");
        assertEquals(True, True);
        assertNotEquals(True, False);
        assertEquals(True, true);
        assertEquals(False, false);
    }

    @Test
    public void hashCode_() {
        PyObject HashObject = pyobjecttest.get("HashObject");
        assertEquals(Integer.MAX_VALUE,  HashObject.call(Integer.MAX_VALUE).hashCode());
        assertEquals(1,  HashObject.call(1).hashCode());
        assertEquals(0,  HashObject.call(0).hashCode());
        assertEquals(-2,  HashObject.call(-1).hashCode());  // CPython implementation detail
        assertEquals(-2,  HashObject.call(-2).hashCode());
        assertEquals(-3,  HashObject.call(-3).hashCode());
        assertEquals(Integer.MIN_VALUE,  HashObject.call(Integer.MIN_VALUE).hashCode());
    }

    @Test
    public void toString_() {
        assertEquals("hello", pyobjecttest.get("str_var").toString());
        assertEquals("True", pyobjecttest.get("bool_var").toString());
        assertEquals("43.5", pyobjecttest.get("float_var").toString());
    }

    @Test
    public void repr() {
        assertEquals("'hello'", pyobjecttest.get("str_var").repr());
    }

    @SuppressWarnings({"UnusedAssignment", "unused"})
    @Test
    public void finalize_() {
        PyObject DT = pyobjecttest.get("DelTrigger");
        PyObject TestCase = python.getModule("unittest").get("TestCase");
        PyObject test = TestCase.call("__init__");  // https://stackoverflow.com/a/18084492/220765

        DT.callAttr("reset");
        PyObject dt = DT.call();
        DT.callAttr("assertTriggered", test, false);
        dt.toString();  // Prevent Android Studio 3.1 release build from nulling dt prematurely.
        dt = null;
        DT.callAttr("assertTriggered", test, true);
    }

}
