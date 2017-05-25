package com.chaquo.python;

/** Platform for a normal Python installation. */
public class GenericPlatform implements Python.Platform {
    private String mPath = System.getenv("PYTHONPATH");
    private boolean mShouldInitialize = true;

    public GenericPlatform() {
        System.loadLibrary("chaquopy_java");
    }

    @Override
    public boolean shouldInitialize() {
        return mShouldInitialize;
    }

    @Override
    public String getPath() {
        return mPath;
    }

    public GenericPlatform setPath(String path) {
        mPath = path;
        return this;
    }

    public GenericPlatform setShouldInitialize(boolean shouldInitialize) {
        mShouldInitialize = shouldInitialize;
        return this;
    }
}
