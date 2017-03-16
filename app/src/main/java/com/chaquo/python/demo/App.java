package com.chaquo.python.demo;

import android.app.*;
import android.content.*;
import android.preference.*;


public class App extends Application {

    static Context context;
    static SharedPreferences prefs;

    @Override
    public void onCreate() {
        super.onCreate();
        context = this;
        prefs = PreferenceManager.getDefaultSharedPreferences(this);
    }

}