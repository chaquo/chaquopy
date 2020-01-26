package com.chaquo.python.demo;

import android.app.*;
import android.os.*;
import android.text.*;
import android.widget.*;


public class PackageTestActivity extends PythonTestActivity {

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        // VISIBLE_PASSWORD is necessary to prevent some versions of the Google keyboard from
        // displaying the suggestion bar.
        ((TextView) findViewById(resId("id", "etInput"))).setInputType(
            InputType.TYPE_CLASS_TEXT +
            InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS +
            InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD);
    }

    @Override protected Class<? extends Task> getTaskClass() {
        return Task.class;
    }

    // =============================================================================================

    public static class Task extends PythonTestActivity.Task {
        public Task(Application app) {
            super(app, STDIN_ENABLED);  // For interactive debugging using pdb.
        }
    }
}