package com.chaquo.python.demo;

import android.os.*;
import android.support.v7.app.*;
import android.support.v7.preference.*;
import com.chaquo.python.*;

public class MainActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (! Python.isStarted()) {
            Python.start(new AndroidPlatform(this));
        }
        getSupportFragmentManager().beginTransaction()
            .replace(android.R.id.content, new MenuFragment())
            .commit();
    }

    public static class MenuFragment extends PreferenceFragmentCompat {
        @Override
        public void onCreatePreferences(Bundle savedInstanceState, String rootKey) {
            addPreferencesFromResource(R.xml.activity_main);
        }
    }
}
