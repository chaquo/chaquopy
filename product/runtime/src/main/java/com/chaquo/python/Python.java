package com.chaquo.python;


public class Python {
    public interface Platform {
        /** @return the value to assign to PYTHONPATH */
        String getPath();
    }

    /** @hide (FIXME http://stackoverflow.com/questions/35076307/javadoc-hide-cant-work) */
    public static boolean sStarted;  // Set by Python function start_jvm

    private static Python sInstance;

    public static Python getInstance() {
        if (sInstance == null) {
            try {
                start(new GenericPlatform());
            } catch (PyException e) {
                throw new RuntimeException(e);
            }
        }
        return sInstance;
    }

    public static Python start(Platform platform) throws PyException {
        if (sInstance != null) {
            throw new IllegalStateException("Python already started");
        }
        if (! sStarted) {
            start(platform.getPath());
            sStarted = true;
        }
        sInstance = new Python(platform);
        return sInstance;
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
