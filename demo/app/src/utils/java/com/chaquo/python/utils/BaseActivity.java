package com.chaquo.python.utils;

import android.os.*;
import android.view.*;

import androidx.appcompat.app.*;

import com.chaquo.python.*;

public class BaseActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        PyObject platform = Python.getInstance().getModule("platform");
        getSupportActionBar().setSubtitle(
            "Python " + platform.callAttr("python_version").toString()
        );
    }

    @Override
    public void setContentView(int layoutResID) {
        super.setContentView(layoutResID);

        // On API levels 35 and higher, which use edge to edge layout, this adds
        // padding to avoid overlapping the status bar, navigation bar, and any
        // cutouts. On lower API levels, it appears to have no effect.
        ((ViewGroup)findViewById(android.R.id.content)).getChildAt(0)
            .setFitsSystemWindows(true);
    }
}
