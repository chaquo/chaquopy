package com.chaquo.python.demo;

import android.os.*;
import com.chaquo.python.*;

public abstract class PythonConsoleActivity extends ConsoleActivity {

    protected Python py;
    private PyObject prevStdout, prevStderr;

    @Override protected void onCreate(Bundle savedInstanceState) {
        py = Python.getInstance();
        super.onCreate(savedInstanceState);
    }

    @Override protected void onStart() {
        super.onStart();
        PyObject utils = py.getModule("chaquopy.demo.utils");
        PyObject JavaTeeOutputStream = utils.get("JavaTeeOutputStream");
        PyObject sys = py.getModule("sys");
        prevStdout = sys.get("stdout");
        prevStderr = sys.get("stderr");
        sys.put("stdout", JavaTeeOutputStream.call(prevStdout, this, "output"));
        sys.put("stderr", JavaTeeOutputStream.call(prevStderr, this, "outputError"));
    }

    @Override protected void onStop() {
        super.onStop();
        PyObject sys = py.getModule("sys");
        sys.put("stdout", prevStdout);
        sys.put("stderr", prevStderr);
    }

}
