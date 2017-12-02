package com.chaquo.python;

/** Platform for a normal Python installation. */
public class GenericPlatform extends Python.Platform {
    private String mPath = System.getenv("PYTHONPATH");

    public GenericPlatform() {
        if (System.getProperty("java.vendor").toLowerCase().contains("android")) {
            throw new RuntimeException("Cannot use GenericPlatform on Android. Call Python.start" +
                                       "(new AndroidPlatform(context)) before Python.getInstance().");
        }
        System.loadLibrary("chaquopy_java");
    }

    @Override
    public String getPath() {
        return mPath;
    }

    /** Sets the value to assign to `PYTHONPATH`. */
    public GenericPlatform setPath(String path) {
        mPath = path;
        return this;
    }
}
