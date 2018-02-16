package com.chaquo.python.demo;

import android.os.*;
import android.util.*;
import com.chaquo.python.*;
import java.util.*;

/** Base class for a console-based activity that will run Python code. sys.stdout and sys.stderr
 * will be directed to the output view whenever the activity is on-screen. If the Python code
 * caches their values, it can direct output to the activity even when it's off-screen.
 *
 * The input box will initially be hidden. By default, it will be displayed the first time sys.stdin
 * is read. To prevent this and leave sys.stdin untouched, call setStdinEnabled(false) in onCreate.
 *
 * Initial input can be supplied by calling input(): this will not be displayed on screen until
 * Python starts to read it. */
public abstract class PythonConsoleActivity extends ConsoleActivity
implements ConsoleActivity.InputListener {

    protected Python py;
    private PyObject console, sys;
    private PyObject prevStdin, prevStdout, prevStderr;
    private PyObject stdin;

    private boolean stdinEnabled = true;
    private ArrayList<String> bufferedInput = new ArrayList<>();

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        py = Python.getInstance();
        console = py.getModule("chaquopy.utils.console");
        sys = py.getModule("sys");
    }

    // FIXME "this" passed to both input and output streams will be invalidated by rotation.
    // FIXME input box will also be hidden.
    @Override protected void onStart() {
        super.onStart();
        prevStdin = sys.get("stdin");
        if (stdinEnabled && stdin == null) {
            stdin = console.callAttr("ConsoleInputStream", this);
        }
        sys.put("stdin", stdin);

        prevStdout = sys.get("stdout");
        prevStderr = sys.get("stderr");
        PyObject COS = console.get("ConsoleOutputStream");
        sys.put("stdout", COS.call(this, "output", prevStdout));
        sys.put("stderr", COS.call(this, "outputError", prevStderr));
    }

    @Override protected void onStop() {
        super.onStop();
        sys.put("stdin", prevStdin);
        sys.put("stdout", prevStdout);
        sys.put("stderr", prevStderr);
    }

    // FIXME will send EOF on rotation
    @Override public void onDestroy() {
        super.onDestroy();
        if (stdinEnabled) {
            onInput(null);  // Signals EOF
        }
    }

    /** Must only be called from onCreate. */
    public void setStdinEnabled(boolean enabled) {
        stdinEnabled = enabled;
    }

    @Override public void input(String text) {
        if (getInputListener() == null) {
            bufferedInput.add(text);
        } else {
            super.input(text);
        }
    }

    @SuppressWarnings("unused")  // Called from Python
    public void onInputState(boolean blocked) {
        if (blocked) {
            if (getInputListener() == null) {
                setInputListener(this);
            }
            for (String text : bufferedInput) {
                input(text);
            }
            bufferedInput.clear();
        }
    }

    @Override public void onInput(String text) {
        if (text != null) {
            Log.i("python.stdin", text);
        }
        stdin.callAttr("on_input", text);
    }

}
