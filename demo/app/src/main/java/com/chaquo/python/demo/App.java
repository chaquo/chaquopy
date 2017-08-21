package com.chaquo.python.demo;

import android.app.*;
import android.content.*;
import android.preference.*;
import com.chaquo.python.*;


public class App extends Application {

    static App context;
    static SharedPreferences prefs;

    @Override
    public void onCreate() {
        super.onCreate();
        context = this;
        prefs = PreferenceManager.getDefaultSharedPreferences(this);

        Python.start(new AndroidPlatform(this));
    }

}