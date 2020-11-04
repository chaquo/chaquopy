package com.chaquo.python.utils;

import android.app.*;
import android.text.*;
import com.chaquo.python.*;

public class PythonTestActivity extends PythonConsoleActivity {

    @Override protected Class<? extends Task> getTaskClass() {
        return Task.class;
    }

    // =============================================================================================

    public static class Task extends PythonConsoleActivity.Task {
        public Task(Application app) {
            super(app, InputType.TYPE_NULL);  // test_android expects stdin to return EOF.
        }

        @SuppressWarnings("unused")  // For pkgtest app.
        public Task(Application app, int inputType) {
            super(app, inputType);
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
