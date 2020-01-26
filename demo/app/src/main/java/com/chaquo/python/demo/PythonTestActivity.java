package com.chaquo.python.demo;

import android.app.*;
import com.chaquo.python.*;
import com.chaquo.python.utils.*;

public class PythonTestActivity extends PythonConsoleActivity {

    @Override protected Class<? extends Task> getTaskClass() {
        return Task.class;
    }

    // =============================================================================================

    public static class Task extends PythonConsoleActivity.Task {
        public Task(Application app) {
            this(app, STDIN_DISABLED);  // test_android expects stdin to return EOF.
        }

        public Task(Application app, int flags) {
            super(app, flags);
        }

        @Override public void run() {
            PyObject unittest = py.getModule("unittest");
            PyObject runner = unittest.callAttr("TextTestRunner", new Kwarg("verbosity", 2));
            PyObject loader = unittest.get("defaultTestLoader");
            PyObject suite = loader.callAttr("loadTestsFromModule", py.getModule("chaquopy.test"));
            runner.callAttr("run", suite);
        }
    }

}
