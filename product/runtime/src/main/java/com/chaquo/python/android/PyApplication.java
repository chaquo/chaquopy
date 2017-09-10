package com.chaquo.python.android;

import android.app.Application;
import com.chaquo.python.*;


/** Application subclass which automatically starts Python. */
public class PyApplication extends Application {

    /** Starts Python.
     *
     * If you override this method you *must* call through to the superclass implementation. */
    @Override
    public void onCreate() {
        super.onCreate();
        Python.start(new AndroidPlatform(this));
    }

}
