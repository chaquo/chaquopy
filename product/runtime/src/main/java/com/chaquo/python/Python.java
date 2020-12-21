package com.chaquo.python;


import org.jetbrains.annotations.*;

/** <p>Interface to Python.</p>
 *
 * <p>Unless otherwise specified, all methods in this class throw {@link PyException} on
 * failure.</p> */
public class Python {

    /** Provides information needed to start Python. */
    public static class Platform {
        /** Returns the value to assign to {@code PYTHONPATH}, or {@code null} to leave it
         * unset. The default implementation returns {@code null}. */
        public String getPath() { return null; }

        /** Called after Python is started. The default implementation does nothing. */
        public void onStart(@NotNull Python py) {}
    }

    private static Platform platform;
    private static boolean failed;
    private static Python instance = new Python();

    /** Gets the interface to Python. This method always returns the same object. If
     * {@link #start start()} has not yet been called, it will be called with a new
     * {@link GenericPlatform}. */
    public static synchronized @NotNull Python getInstance() {
        if (! isStarted()) {
            start(new GenericPlatform());
        }
        return instance;
    }

    /** <p>Starts Python. If this method is called, it can only be called once, and it must be
     * before any call to {@link #getInstance}.</p>
     *
     * <p>If running on Android, make sure you read the <a
     * href="../../../../android.html#android-startup">notes on how to call this method in your
     * app</a>. */
    public static synchronized void start(@NotNull Platform platform) {
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

    /** Returns the Platform object which was used to start Python, or {@code null} if {@link
     * #start start} has not been called. */
    public static synchronized Platform getPlatform() {
        return platform;
    }

    /** Returns whether Python is running. */
    public static synchronized boolean isStarted() {
        return (platform != null);
    }

    /** There is no stop() method, because Py_Finalize does not guarantee an orderly or complete
     * cleanup. */
    private static native void startNative(Platform platform, String pythonPath);

    // =======================================================================

    private Python() {}

    /** Returns the Python module with the given name. Dot notation may be used to get
     * submodules (e.g. {@code os.path}). */
    @SuppressWarnings("deprecation")
    public @NotNull PyObject getModule(@NotNull String name) {
        return PyObject.getInstance(getModuleNative(name));
    }
    private native long getModuleNative(String name);

    /** Returns the <a href="https://docs.python.org/3/library/builtins.html">{@code
     * builtins}</a> module. This contains Python's built-in functions (e.g. {@code open}),
     * types (e.g. {@code dict}), constants (e.g. {@code True}) and exceptions (e.g. {@code
     * ValueError}). */
    public @NotNull PyObject getBuiltins() {
        return getModule("builtins");
    }
}
