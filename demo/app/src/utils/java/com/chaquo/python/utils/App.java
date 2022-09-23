package com.chaquo.python.utils;

import android.content.*;
import androidx.preference.*;
import com.chaquo.python.android.*;


public class App extends PyApplication {

    public static App context;
    public static SharedPreferences prefs;

    @Override
    public void onCreate() {
        super.onCreate();
        context = this;
        prefs = PreferenceManager.getDefaultSharedPreferences(this);
    }

}