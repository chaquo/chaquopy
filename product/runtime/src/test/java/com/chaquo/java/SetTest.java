package com.chaquo.java;

import com.chaquo.python.*;
import java.util.*;
import org.junit.*;
import org.junit.runners.*;

import static com.chaquo.python.PyObject.fromJava;
import static org.junit.Assert.*;


@SuppressWarnings("SuspiciousMethodCalls")
@FixMethodOrder(MethodSorters.NAME_ASCENDING)
public class SetTest extends ContainerTest {

    private Set<PyObject> emptySet = mod.callAttr("new_set").asSet();
    private Set<PyObject> intSet = mod.callAttr("new_set", 10, 11, 12).asSet();
    private Set<PyObject> intSetRO = mod.callAttr("new_set_ro", 10, 11, 12).asSet();

    @Test
    public void ctor_unsupported() {
        expectUnsupported("int", "__contains__");
        fromJava(42).asSet();
    }


    // === Read methods ======================================================

    public void size() {
        assertEquals(0, emptySet.size());
        assertEquals(2, intSet.size());
    }

    @Test
    public void contains() {
        assertFalse(emptySet.contains(10));

        assertTrue(intSet.contains(10));
        assertTrue(intSet.contains(11));
        assertTrue(intSet.contains(12));
        assertFalse(intSet.contains(13));
    }

    @Test
    public void iterator() {
        Set<Integer> actual = new HashSet<>();
        int count = 0;
        for (PyObject obj : intSet) {
            actual.add(obj.toInt());
            count++;
        }
        assertEquals(3, count);
        assertEquals(new HashSet<>(Arrays.asList(10, 11, 12)), actual);

        count = 0;
        for (PyObject obj : emptySet) {
            count++;
        }
        assertEquals(0, count);
    }

    @Test
    public void iterator_remove() {
        Iterator<PyObject> i = intSet.iterator();
        i.next();
        thrown.expect(UnsupportedOperationException.class);
        thrown.expectMessage("Python does not support removing from a container while " +
                              "iterating over it");
        i.remove();
    }


    // === Modification methods ==============================================

    @Test
    public void add() {
        assertFalse(intSet.add(fromJava(10)));
        assertEquals(3, intSet.size());
        assertTrue(intSet.add(fromJava(13)));
        assertEquals(4, intSet.size());
    }

    @Test
    public void add_unsupportedPresent() {
        expectUnsupported("frozenset", "add");
        intSetRO.add(fromJava(10));
    }

    @Test
    public void add_unsupportedAbsent() {
        expectUnsupported("frozenset", "add");
        intSetRO.add(fromJava(13));
    }

    @Test
    public void remove() {
        assertTrue(intSet.remove(fromJava(10)));
        assertEquals(2, intSet.size());
        assertFalse(intSet.remove(fromJava(13)));
        assertEquals(2, intSet.size());
    }

    @Test
    public void remove_unsupportedPresent() {
        expectUnsupported("frozenset", "remove");
        intSetRO.remove(fromJava(10));
    }

    @Test
    public void remove_unsupportedAbsent() {
        expectUnsupported("frozenset", "remove");
        intSetRO.remove(fromJava(13));
    }

    @Test
    public void clear() {
        intSet.clear();
        assertEquals(0, intSet.size());

        emptySet.clear();
        assertEquals(0, emptySet.size());
    }

    @Test
    public void clear_unsupported() {
        expectUnsupported("frozenset", "clear");
        intSetRO.clear();
    }
}
