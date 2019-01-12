package com.chaquo.java;

import com.chaquo.python.*;
import java.util.*;
import org.junit.*;
import org.junit.runners.*;

import static com.chaquo.python.PyObject.fromJava;
import static org.junit.Assert.*;


@FixMethodOrder(MethodSorters.NAME_ASCENDING)
public class ListTest extends ContainerTest {

    private List<PyObject> emptyList = mod.callAttr("new_list").asList();
    private List<PyObject> strList = mod.callAttr("new_list", "hello", "world").asList();
    private List<PyObject> intList = mod.callAttr("new_list", 10, 11, 12).asList();
    private List<PyObject> intListRO = mod.callAttr("new_list_ro", 20, 21, 22).asList();
    private List<PyObject> str = fromJava("hello").asList();

    private void expectOutOfBounds(String prefix) {
        thrown.expect(IndexOutOfBoundsException.class);
        thrown.expectMessage(prefix + " index out of range");
    }

    @Test
    public void ctor_unsupported() {
        expectUnsupported("int", "__getitem__");
        fromJava(42).asList();
    }


    // === Read methods ======================================================

    @Test
    public void size() {
        assertEquals(0, emptyList.size());
        assertEquals(2, strList.size());
        assertEquals(3, intList.size());
    }

    @Test
    public void get() {
        assertEquals(10, intList.get(0).toInt());
        assertEquals(11, intList.get(1).toInt());
        assertEquals(12, intList.get(2).toInt());

        assertEquals(20, intListRO.get(0).toInt());
        assertEquals(21, intListRO.get(1).toInt());
        assertEquals(22, intListRO.get(2).toInt());
    }

    @Test
    public void get_bounds() {
        expectOutOfBounds("list");
        intList.get(3);
    }

    @Test
    public void get_boundsEmpty() {
        expectOutOfBounds("list");
        emptyList.get(0);
    }

    @Test
    @SuppressWarnings("ConstantConditions")
    public void get_boundsNegative() {
        expectOutOfBounds("list");
        intList.get(-1);
    }

    @Test
    public void iterator() {
        List<String> actual = new ArrayList<>();
        for (PyObject obj: strList) {
            actual.add(obj.toString());
        }
        assertEquals(Arrays.asList("hello", "world"), actual);

        actual.clear();
        for (PyObject obj: emptyList) {
            actual.add(obj.toString());
        }
        assertTrue(actual.isEmpty());
    }


    // === Modification methods ==============================================

    @Test
    public void set() {
        assertEquals(10, intList.set(0, fromJava(40)).toInt());
        assertEquals(11, intList.set(1, fromJava(41)).toInt());
        assertEquals(12, intList.set(2, fromJava(42)).toInt());

        assertEquals(40, intList.set(0, fromJava(50)).toInt());
        assertEquals(50, intList.get(0).toInt());
        assertEquals(41, intList.get(1).toInt());
        assertEquals(42, intList.get(2).toInt());
    }

    @Test
    public void set_bounds() {
        expectOutOfBounds("list");
        intList.set(3, fromJava(42));
    }

    @Test
    public void set_unsupported() {
        expectUnsupported("tuple", "__setitem__");
        intListRO.set(0, fromJava(42));
    }

    @Test
    public void add() {
        // End
        intList.add(3, fromJava(13));
        assertEquals(4, intList.size());
        assertEquals(13, intList.get(3).toInt());

        // Middle
        assertEquals(11, intList.get(1).toInt());
        intList.add(1, fromJava(14));
        assertEquals(5, intList.size());
        assertEquals(14, intList.get(1).toInt());
        assertEquals(11, intList.get(2).toInt());

        // Start
        intList.add(0, fromJava(15));
        assertEquals(6, intList.size());
        assertEquals(15, intList.get(0).toInt());
        assertEquals(10, intList.get(1).toInt());
        assertEquals(14, intList.get(2).toInt());
    }

    @Test
    public void add_end() {
        assertTrue(intList.add(fromJava(42)));
        assertEquals(4, intList.size());
        assertEquals(42, intList.get(3).toInt());
    }

    @Test
    public void add_bounds() {
        expectOutOfBounds("list");
        intList.add(4, fromJava(42));
    }

    @Test
    public void add_unsupported() {
        expectUnsupported("tuple", "insert");
        intListRO.add(fromJava(42));
    }

    @Test
    public void remove() {
        assertEquals(11, intList.get(1).toInt());
        assertEquals(12, intList.get(2).toInt());
        assertEquals(11, intList.remove(1).toInt());
        assertEquals(2, intList.size());
        assertEquals(12, intList.get(1).toInt());
    }

    @Test
    public void remove_bounds() {
        expectOutOfBounds("list");
        intList.remove(3);
    }

    @Test
    public void remove_unsupported() {
        expectUnsupported("tuple", "pop");
        intListRO.remove(0);
    }

    @Test
    public void clear() {
        intList.clear();
        assertEquals(0, intList.size());

        emptyList.clear();
        assertEquals(0, emptyList.size());
    }

    @Test
    public void clear_unsupported() {
        expectUnsupported("tuple", "clear");
        intListRO.clear();
    }


    // === Other sequence types ==============================================

    @Test
    public void str() {
        assertEquals(5, str.size());
        assertEquals('e', str.get(1).toChar());
    }

    @Test
    public void str_bounds() {
        expectOutOfBounds("str");
        str.get(5);
    }

    @Test
    public void str_unsupported() {
        expectUnsupported("str", "__setitem__");
        str.set(0, fromJava("j"));
    }

}
