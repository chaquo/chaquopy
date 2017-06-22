package com.chaquo.python.demo;

import android.os.*;
import android.support.v7.app.*;
import android.support.v7.preference.*;
import android.text.method.*;
import android.widget.*;
import com.chaquo.python.*;

public class MainActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (! Python.isStarted()) {
            Python.start(new AndroidPlatform(this));
        }

        setContentView(R.layout.activity_main);
        getSupportFragmentManager().beginTransaction()
            .replace(R.id.flMenu, new MenuFragment())
            .commit();

        ((TextView)findViewById(R.id.tvCaption)).setMovementMethod(LinkMovementMethod.getInstance());
    }

    public static class MenuFragment extends PreferenceFragmentCompat {
        @Override
        public void onCreatePreferences(Bundle savedInstanceState, String rootKey) {
            addPreferencesFromResource(R.xml.activity_main);
        }
    }
}
