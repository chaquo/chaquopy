package com.chaquo.python.demo;

import android.os.*;
import android.text.*;
import android.text.style.*;
import com.chaquo.python.*;


/** Redirects Python's stdin, stdout and stderr to connect to the activity UI. */
public abstract class PythonConsoleActivity extends ConsoleActivity {

    protected Python py;
    private PyObject stdin;
    private PyObject prevStdout, prevStderr, prevStdin;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        py = Python.getInstance();
    }

    @Override
    protected void onStart() {
        super.onStart();
        PyObject utils = py.getModule("chaquopy.utils.console");
        PyObject sys = py.getModule("sys");

        prevStdout = sys.get("stdout");
        prevStderr = sys.get("stderr");
        sys.put("stdout", utils.callAttr("ConsoleOutputStream", prevStdout, this, "output"));
        sys.put("stderr", utils.callAttr("ConsoleOutputStream", prevStderr, this, "outputStderr"));

        prevStdin = sys.get("stdin");
        stdin = utils.callAttr("ConsoleInputStream");
        sys.put("stdin", stdin);
    }

    protected void outputStderr(CharSequence text) {
        SpannableString spanText = new SpannableString(text);
        spanText.setSpan(new ForegroundColorSpan(getResources().getColor(R.color.stderr)),
                         0, text.length(), 0);
        output(spanText);
    }

    @Override
    protected void onInput(String input) {
        stdin.callAttr("on_input", input);
    }

    @Override
    protected void onStop() {
        super.onStop();
        PyObject sys = py.getModule("sys");
        sys.put("stdout", prevStdout);
        sys.put("stderr", prevStderr);
        sys.put("stdin", prevStdin);
    }

}
