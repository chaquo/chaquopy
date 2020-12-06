package com.chaquo.python;


/** Interface to Python.
 *
 * Unless otherwise specified, all methods in this class throw {@link PyException} on failure. */
public class Python {

    /** Provides information needed to start Python. */
    public static class Platform {
        /** Returns the value to assign to `PYTHONPATH`, or `null` to leave it unset. The default
         * implementation returns `null`. */
        public String getPath() { return null; }

        /** Called after Python is started. The default implementation does nothing. */
        public void onStart(Python py) {}
    }

    private static Platform platform;
    private static boolean failed;
    private static Python instance = new Python();

    /** Gets the interface to Python. This method always returns the same object. If
     * {@link #start start()} has not yet been called, it will be called with a new
     * {@link GenericPlatform}. */
    public static synchronized Python getInstance() {
        if (! isStarted()) {
            start(new GenericPlatform());
        }
        return instance;
    }

    /** Starts the Python virtual machine. If this method is called, it can only be called once, and
     * it must be before any call to {@link #getInstance}.
     *
     * If running on Android, see the notes <a
     * href="../../../../android.html#android-startup">here</a> on how to call this method in an
     * app. If running on any other platform, there's no need to call this method, unless you want
     * to customize the Python startup process.
     **/
    public static synchronized void start(Platform platform) {
        if (isStarted()) {
            throw new IllegalStateException("Python already started");
        }
        if (failed) {
            // startNative will cause a native crash if called more than once.
            throw new IllegalStateException("Python startup previously failed, and cannot be retried");
        }
        try {
            startNative(platform, platform.getPath());
            platform.onStart(instance);
            Python.platform = platform;
        } catch (Throwable e) {
            failed = true;
            throw e;
        }
    }

    /** Returns the Platform object which was used to start Python, or `null` if Python has not
     * yet been started. */
    public static synchronized Platform getPlatform() {
        return platform;
    }

    /** Return whether the Python virtual machine is running */
    public static synchronized boolean isStarted() {
        return (platform != null);
    }

    /** There is no stop() method, because Py_Finalize does not guarantee an orderly or complete
     * cleanup. */
    private static native void startNative(Platform platform, String pythonPath);

    // =======================================================================

    private Python() {}

    /** Returns the module with the given name. Dot notation may be used to get submodules (e.g.
     * `os.path`). */
    @SuppressWarnings("deprecation")
    public PyObject getModule(String name) {
        return PyObject.getInstance(getModuleNative(name));
    }
    private native long getModuleNative(String name);

    /** Returns the <a href="https://docs.python.org/3/library/builtins.html">`builtins`</a>
     * module, which contains Python's built-in functions (e.g. `open`), types (e.g. `dict`),
     * constants (e.g. `True`) and exceptions (e.g. `ValueError`). */
    public PyObject getBuiltins() {
        return getModule("builtins");
    }
}
