package com.chaquo.python;

/** Platform for a normal Python installation. If no path is specified in the constructor, the
 * `PYTHONPATH` environment variable will be used. */
public class GenericPlatform implements Python.Platform {
    private String mPath;

    public GenericPlatform() {
        System.loadLibrary("chaquopy_java");
    }

    public GenericPlatform(String path) {
        this();
        mPath = path;
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
