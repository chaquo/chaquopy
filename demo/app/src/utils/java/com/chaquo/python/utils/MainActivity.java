package com.chaquo.python.utils;

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
        App.setPySubtitle(this);

        setContentView(resId("layout", "activity_menu"));
        ((TextView)findViewById(resId("id", "tvCaption")))
            .setText(resId("string", "main_caption"));
        getSupportFragmentManager().beginTransaction()
            .replace(resId("id", "flMenu"), new MenuFragment())
            .commit();

        ((TextView)findViewById(resId("id", "tvCaption"))).setMovementMethod(LinkMovementMethod.getInstance());
    }

    public static class MenuFragment extends PreferenceFragmentCompat {
        @Override
        public void onCreatePreferences(Bundle savedInstanceState, String rootKey) {
            addPreferencesFromResource(Utils.resId(getContext(), "xml", "activity_main"));
        }
    }

    public int resId(String type, String name) {
        return Utils.resId(this, type, name);
    }
}
