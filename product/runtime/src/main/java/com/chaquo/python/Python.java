package com.chaquo.python;


public class Python {

    public interface Platform {
        /** @return the value to assign to PYTHONPATH */
        String getPath();
    }

    private static Python sInstance;

    public static Python start(Platform platform) {
        if (sInstance == null) {
            sInstance = new Python(platform);
        } else {
            throw new IllegalArgumentException("Python already started");
        }
        return sInstance;
    }

    public static Python getInstance() {
        if (sInstance == null) {
            start(new GenericPlatform());
        }
        return sInstance;
    }


    private Platform mPlatform;

    public Python(Platform platform) {
        mPlatform = platform;
        start(platform.getPath());
    }

    /** There is no stop() method, because Py_Finalize does not guarantee an orderly or complete
     * cleanup. */
    private native void start(String pythonPath);

    public native PyObject getModule(String name) throws PyException;

    public native String hello(String str);
    public native int add(int x);
}
