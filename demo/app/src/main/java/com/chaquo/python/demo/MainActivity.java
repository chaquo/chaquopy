package com.chaquo.python.demo;

import android.content.pm.*;
import android.os.*;
import android.text.method.*;
import android.widget.*;
import androidx.appcompat.app.*;
import androidx.preference.*;

public class MainActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        try {
            String version = getPackageManager().getPackageInfo(getPackageName(), 0).versionName;
            setTitle(getTitle() + " " + version);
        } catch (PackageManager.NameNotFoundException ignored) {}

        setContentView(R.layout.activity_menu);
        ((TextView)findViewById(R.id.tvCaption)).setText(R.string.main_caption);
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
