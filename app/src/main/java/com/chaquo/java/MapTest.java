package com.chaquo.java;

import com.chaquo.python.*;
import java.util.*;
import org.junit.*;
import org.junit.runners.*;

import static com.chaquo.python.PyObject.fromJava;
import static java.util.Map.Entry;
import static org.junit.Assert.*;


@SuppressWarnings({"SuspiciousMethodCalls"})
@FixMethodOrder(MethodSorters.NAME_ASCENDING)
public class MapTest extends ContainerTest {

    private Map<PyObject, PyObject> emptyMap = mod.callAttr("new_map").asMap();
    private Map<PyObject, PyObject> strIntMap =
        mod.callAttr("new_map", "a", 1, "b", 2).asMap();
    private Map<PyObject, PyObject> strIntMapRO =
        mod.callAttr("new_map_ro", "a", 1, "b", 2).asMap();
    private Map<PyObject, PyObject> nullKeyMap =
        mod.callAttr("new_map", null, "null", 1, "one").asMap();
    private Map<PyObject, PyObject> nullValueMap =
        mod.callAttr("new_map", "null", null, "one", 1).asMap();

    @Test
    public void ctor_unsupported() {
        expectUnsupported("int", "__contains__");
        fromJava(42).asMap();
    }

    @Test
    public void entrySet() {
        Set<Entry<PyObject, PyObject>> es = strIntMap.entrySet();
        assertEquals(2, es.size());

        Map<String, Integer> expected = new HashMap<>();
        expected.put("a", 1);
        expected.put("b", 2);
        for (Entry<PyObject, PyObject> entry : strIntMap.entrySet()) {
            assertEquals(expected.remove(entry.getKey().toString()).intValue(),
                         entry.getValue().toInt());
        }
        assertTrue(expected.isEmpty());
    }

    @Test
    public void entrySet_empty() {
        Set<Entry<PyObject, PyObject>> ks = emptyMap.entrySet();
        assertEquals(0, ks.size());
        Iterator<Entry<PyObject, PyObject>> i = ks.iterator();
        assertFalse(i.hasNext());

        thrown.expect(NoSuchElementException.class);
        i.next();
    }

    @Test
    public void entrySet_setValue() {
        for (Entry<PyObject, PyObject> entry : strIntMap.entrySet()) {
            if (entry.getKey().toString().equals("b")) {
                entry.setValue(fromJava(99));
            }
        }
        assertEquals(1, strIntMap.get("a").toInt());
        assertEquals(99, strIntMap.get("b").toInt());
    }

    @Test
    public void entrySet_remove() {
        Iterator<Entry<PyObject, PyObject>> i = strIntMap.entrySet().iterator();
        i.next();
        thrown.expect(UnsupportedOperationException.class);
        thrown.expectMessage("Python does not support removing from a container while " +
                              "iterating over it");
        i.remove();
    }


    // === Read methods ======================================================

    @Test
    public void size() {
        assertEquals(0, emptyMap.size());
        assertEquals(2, strIntMap.size());
    }

    @Test
    public void contains() {
        assertFalse(emptyMap.containsKey("a"));
        assertFalse(emptyMap.containsKey(null));

        assertTrue(strIntMap.containsKey("a"));
        assertTrue(strIntMap.containsKey("b"));
        assertFalse(strIntMap.containsKey("c"));
        assertFalse(strIntMap.containsKey(null));

        assertTrue(nullKeyMap.containsKey(null));
        assertFalse(nullKeyMap.containsKey("null"));
        assertTrue(nullKeyMap.containsKey(1));
        assertFalse(nullKeyMap.containsKey("one"));

        assertTrue(nullValueMap.containsKey("null"));
        assertFalse(nullValueMap.containsKey(null));
        assertTrue(nullValueMap.containsKey("one"));
        assertFalse(nullValueMap.containsKey(1));
    }

    @Test
    public void get() {
        assertNull(emptyMap.get("a"));
        assertNull(emptyMap.get(null));

        assertEquals(1, strIntMap.get("a").toInt());
        assertEquals(2, strIntMap.get("b").toInt());
        assertNull(strIntMap.get("c"));
        assertNull(strIntMap.get(null));

        assertEquals("null", nullKeyMap.get(null).toString());
        assertNull(nullKeyMap.get("null"));
        assertEquals("one", nullKeyMap.get(1).toString());
        assertNull(nullKeyMap.get("one"));

        assertNull(nullValueMap.get("null"));
        assertNull(nullValueMap.get(null));
        assertEquals(1, nullValueMap.get("one").toInt());
        assertNull(nullValueMap.get(1));
    }


    // === Modification methods ==============================================

    @Test
    public void put() {
        strIntMap.put(fromJava("a"), fromJava(101));
        assertEquals(101, strIntMap.get("a").toInt());
        assertEquals(2, strIntMap.size());

        strIntMap.put(fromJava("c"), fromJava(102));
        assertEquals(102, strIntMap.get("c").toInt());
        assertEquals(3, strIntMap.size());
    }

    @Test
    public void put_unsupported() {
        expectUnsupported("mappingproxy", "__setitem__");
        strIntMapRO.put(fromJava("a"), fromJava(101));
    }

    @Test
    public void remove() {
        assertEquals(2, strIntMap.remove("b").toInt());
        assertEquals(1, strIntMap.size());
        assertEquals(1, strIntMap.remove("a").toInt());
        assertEquals(0, strIntMap.size());
    }

    @Test
    public void remove_unsupported() {
        expectUnsupported("mappingproxy", "pop");
        strIntMapRO.remove("b");
    }

    @Test
    public void clear() {
        strIntMap.clear();
        assertEquals(0, strIntMap.size());

        emptyMap.clear();
        assertEquals(0, emptyMap.size());
    }

    @Test
    public void clear_unsupported() {
        expectUnsupported("mappingproxy", "clear");
        strIntMapRO.clear();
    }
}
