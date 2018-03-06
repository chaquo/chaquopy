package com.chaquo.python.demo;

import android.app.*;
import com.chaquo.python.utils.*;

public class ReplActivity extends PythonConsoleActivity {

    @Override protected Class<? extends Task> getTaskClass() {
        return Task.class;
    }

    // Maintain REPL state unless the loop has been terminated, e.g. by typing `exit()`. Requires
    // the activity to be in its own task (see AndroidManifest).
    @Override public void onBackPressed() {
        if (task.thread.isAlive()) {
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
