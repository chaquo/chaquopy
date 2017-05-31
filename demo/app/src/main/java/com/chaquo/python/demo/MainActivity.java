package com.chaquo.python.demo;

import android.os.*;
import android.preference.*;

import com.chaquo.python.*;

public class MainActivity extends PreferenceActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (! Python.isStarted()) {
            Python.start(new AndroidPlatform(this));
        }
        addPreferencesFromResource(R.xml.activity_main);
    }
}
