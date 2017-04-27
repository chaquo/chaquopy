package com.chaquo.python;

public class GenericPlatform implements Python.Platform {
    public GenericPlatform() {
        System.loadLibrary("chaquopy_java");
    }

    @Override
    public String getPath() {
        return null;
    }
}
