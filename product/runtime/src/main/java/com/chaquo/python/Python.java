package com.chaquo.python;


public class Python {
    public interface Platform {
        /** @return the value to assign to PYTHONPATH */
        String getPath();
    }

    /** @hide (used in jvm.pxi)
     * FIXME http://stackoverflow.com/questions/35076307/javadoc-hide-cant-work) */
    public static boolean started;

    private static Python instance;

    public static Python getInstance() {
        if (instance == null) {
            try {
                start(new GenericPlatform());
            } catch (PyException e) {
                throw new RuntimeException(e);
            }
        }
        return instance;
    }

    public static Python start(Platform platform) throws PyException {
        if (instance != null) {
            throw new IllegalStateException("Python already started");
        }
        if (!started) {
            start(platform.getPath());
            started = true;
        }
        instance = new Python(platform);
        return instance;
    }

    /** There is no stop() method, because Py_Finalize does not guarantee an orderly or complete
     * cleanup. */
    private static native void start(String pythonPath) throws PyException;

    // ========

    private Platform mPlatform;

    private Python(Platform platform) {
        mPlatform = platform;
    }

    public native PyObject getModule(String name) throws PyException;

    public native String hello(String str);
    public native int add(int x);
}
