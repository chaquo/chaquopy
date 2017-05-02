package com.chaquo.python;


/** Interface to Python */
public class Python {
    /** Provides information needed to start Python */
    public interface Platform {
        /** @return the value to assign to PYTHONPATH */
        String getPath();
    }

    /** @hide (used in jvm.pxi)
     * FIXME http://stackoverflow.com/questions/35076307/javadoc-hide-cant-work) */
    public static boolean started;

    private static Python instance;

    /** Gets the interface to Python. If {@link #start}() has not yet been called, it will be called
     * with a new {@link GenericPlatform}(). */
    public static Python getInstance() throws PyException {
        if (instance == null) {
            start(new GenericPlatform());
        }
        return instance;
    }

    /** Starts Python. If this method is called, it can only be called once, and it must be before
     * any call to {@link #getInstance}, */
    public static synchronized Python start(Platform platform) throws PyException {
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

    /** Returns the module with the given absolute name. */
    public native PyObject getModule(String name) throws PyException;

    /** Returns the module '__builtin__' in Python 2 or 'builtins' in Python 3. This module
     *  contains Python's built-in functions (e.g. open, print), types (e.g. int, dict) and
     *  constants (e.g. None, True). */
    public native PyObject getBuiltins() throws PyException;
}
