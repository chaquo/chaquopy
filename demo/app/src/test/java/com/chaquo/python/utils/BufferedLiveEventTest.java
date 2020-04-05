package com.chaquo.python.utils;

import androidx.annotation.*;
import androidx.arch.core.executor.testing.*;
import androidx.lifecycle.*;
import androidx.lifecycle.Observer;
import java.util.*;
import org.junit.*;
import org.junit.rules.*;

import static androidx.lifecycle.Lifecycle.Event.*;
import static org.junit.Assert.*;

public class BufferedLiveEventTest implements LifecycleOwner {

    @Rule public TestRule instantExecutorRule = new InstantTaskExecutorRule();
    @Rule public ExpectedException thrown = ExpectedException.none();

    private LifecycleRegistry lifecycle = new LifecycleRegistry(this);

    private BufferedLiveEvent<String> ble = new BufferedLiveEvent<>();

    private static class MockObserver<T> implements Observer<T> {
        public List<T> observed = new ArrayList<>();

        @Override public void onChanged(@Nullable T t) {
            observed.add(t);
        }
    }

    private MockObserver<String> observer = new MockObserver<>();

    @Before public void setUp() throws Exception {
        ble.observe(this, observer);
        assertObserved();
    }

    @NonNull @Override public Lifecycle getLifecycle() {
        return lifecycle;
    }

    @Test public void startStopStart() {
        ble.setValue("a");
        assertObserved();
        lifecycle.handleLifecycleEvent(ON_START);
        assertObserved("a");
        ble.setValue("b");
        assertObserved("b");
        ble.setValue("c");
        lifecycle.handleLifecycleEvent(ON_STOP);
        ble.setValue("d");
        ble.setValue("e");
        assertObserved("c");
        lifecycle.handleLifecycleEvent(ON_START);
        assertObserved("d", "e");
    }

    @Test public void nullValue() {
        lifecycle.handleLifecycleEvent(ON_START);
        ble.setValue("a");
        ble.setValue(null);
        ble.setValue("b");
        assertObserved("a", null, "b");
    }

    @Test public void observeMultiple() {
        thrown.expect(IllegalStateException.class);
        thrown.expectMessage("Cannot register multiple observers on a SingleLiveEvent");
        ble.observe(this, new Observer<String>() {
            @Override public void onChanged(@Nullable String s) {}
        });
    }

    @Test public void observeRemoveObserve() {
        lifecycle.handleLifecycleEvent(ON_START);
        ble.setValue("a");
        assertObserved("a");
        ble.removeObserver(observer);
        ble.setValue("c");
        ble.setValue("d");
        assertObserved();
        ble.observe(this, observer);
        assertObserved("c", "d");
    }

    public void assertObserved(String... expected) {
        assertEquals(Arrays.asList(expected), observer.observed);
        observer.observed.clear();
    }

}
