package com.chaquo.python.demo;

import android.content.*;
import android.preference.*;
import com.chaquo.python.android.*;


public class App extends PyApplication {

    static App context;
    static SharedPreferences prefs;

    @Override
    public void onCreate() {
        super.onCreate();
        context = this;
        prefs = PreferenceManager.getDefaultSharedPreferences(this);
    }

}