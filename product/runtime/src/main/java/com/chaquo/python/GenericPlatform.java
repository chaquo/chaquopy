package com.chaquo.python;

/** Platform for a normal Python installation. */
public class GenericPlatform implements Python.Platform {
    private String mPath;

    public GenericPlatform() {
        System.loadLibrary("chaquopy_java");
    }

    public GenericPlatform setPath(String path) {
        mPath = path;
        return this;
    }

    @Override
    public String getPath() {
        String path = mPath;
        if (path == null) {
            path = System.getenv("PYTHONPATH");
        }
        return path;
    }
}
