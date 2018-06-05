package com.chaquo.python.demo;

import android.app.*;
import android.os.*;
import android.text.*;
import android.widget.*;
import com.chaquo.python.utils.*;

public class ReplActivity extends PythonConsoleActivity {

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

    // Maintain REPL state unless the loop has been terminated, e.g. by typing `exit()`. Requires
    // the activity to be in its own task (see AndroidManifest).
    @Override public void onBackPressed() {
        if (task.getState() == Thread.State.RUNNABLE) {
            moveTaskToBack(true);
        } else {
            super.onBackPressed();
        }
    }

    // =============================================================================================

    public static class Task extends PythonConsoleActivity.Task {
        public Task(Application app) {
            super(app);
        }

        @Override public void run() {
            py.getModule("chaquopy.demo.repl")
                .callAttr("AndroidConsole", App.context)
                .callAttr("interact");
        }
    }

}
