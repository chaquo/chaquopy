package com.chaquo.python.utils;

import android.app.*;
import android.content.*;

import androidx.appcompat.app.*;
import androidx.preference.*;

import com.chaquo.python.*;
import com.chaquo.python.android.*;


public class App extends Application {

    public static App context;
    public static SharedPreferences prefs;

    @Override
    public void onCreate() {
        super.onCreate();
        context = this;
        prefs = PreferenceManager.getDefaultSharedPreferences(this);
        AndroidPlatform platform = new AndroidPlatform(this);

        // This is disabled by default to allow test_stream to check the non-redirected
        // state. Re-enable it to see any errors that happen during Python startup.
        // platform.redirectStdioToLogcat();

        Python.start(platform);
    }

    public static void setPySubtitle(AppCompatActivity activity) {
        PyObject platform = Python.getInstance().getModule("platform");
        activity.getSupportActionBar().setSubtitle(
            "Python " + platform.callAttr("python_version").toString());
    }

}