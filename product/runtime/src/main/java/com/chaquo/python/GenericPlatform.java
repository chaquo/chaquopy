package com.chaquo.python;

/** Platform for a normal Python installation. */
public class GenericPlatform implements Python.Platform {
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

    public GenericPlatform setPath(String path) {
        mPath = path;
        return this;
    }
}
