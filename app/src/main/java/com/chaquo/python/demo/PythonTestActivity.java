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
            super(app, STDIN_DISABLED);  // test_android expects stdin to return EOF.
        }

        @Override public void run() {
            PyObject unittest = py.getModule("unittest");
            PyObject stream = py.getModule("sys").get("stdout");  // https://bugs.python.org/issue10786
            PyObject runner = unittest.callAttr("TextTestRunner",
                                                new Kwarg("stream", stream),
                                                new Kwarg("verbosity", 2));
            PyObject loader = unittest.get("defaultTestLoader");
            PyObject suite = loader.callAttr("loadTestsFromModule", py.getModule("chaquopy.test"));
            runner.callAttr("run", suite);
        }
    }

}
