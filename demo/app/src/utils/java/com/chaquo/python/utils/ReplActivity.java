package com.chaquo.python.utils;

import android.app.*;
import android.text.*;

public class ReplActivity extends PythonConsoleActivity {

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
        // VISIBLE_PASSWORD is necessary to prevent some versions of the Google keyboard from
        // displaying the suggestion bar.
        public Task(Application app) {
            super(app, (InputType.TYPE_CLASS_TEXT +
                        InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS +
                        InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD));
        }

        @Override public void run() {
            py.getModule("chaquopy.utils.repl")
                .callAttr("AndroidConsole", App.context)
                .callAttr("interact");
        }
    }

}
