package com.chaquo.python.android;

import android.app.Application;
import com.chaquo.python.*;


/** Application subclass which automatically starts Python. */
public class PyApplication extends Application {

    /** <p>Starts Python.</p>
     *
     * <p>If you override this method you <i>must</i> call through to the superclass
     * implementation.</p> */
    @Override
    public void onCreate() {
        super.onCreate();
        Python.start(new AndroidPlatform(this));
    }

}
