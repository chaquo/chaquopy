package com.chaquo.python.utils;

import android.app.*;
import android.os.*;
import android.text.*;
import android.util.*;
import android.widget.*;
import androidx.lifecycle.*;
import com.chaquo.python.*;

/** Base class for a console-based activity that will run Python code. sys.stdout and sys.stderr
 * will be directed to the output view whenever the activity is resumed. If the Python code
 * caches their values, it can direct output to the activity even when it's paused.
 *
 * Unless inputType is InputType.TYPE_NULL, sys.stdin will also be redirected whenever
 * the activity is resumed. The input box will initially be hidden, and will be displayed the
 * first time sys.stdin is read. */
public abstract class PythonConsoleActivity extends ConsoleActivity {

    protected Task task;

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        task = ViewModelProviders.of(this).get(getTaskClass());
        if (task.inputType != InputType.TYPE_NULL) {
            ((TextView) findViewById(resId("id", "etInput"))).setInputType(task.inputType);
        }
    }

    protected abstract Class<? extends Task> getTaskClass();

    @Override protected void onResume() {
        task.resumeStreams();
        super.onResume();  // Starts the task thread.
    }

    @Override protected void onPause() {
        super.onPause();
        if (! isChangingConfigurations()) {
            task.pauseStreams();
        }
    }

    // =============================================================================================

    public static abstract class Task extends ConsoleActivity.Task {

        protected Python py = Python.getInstance();
        private PyObject console = py.getModule("chaquopy.utils.console");
        private PyObject sys = py.getModule("sys");
        int inputType;
        private PyObject stdin, stdout, stderr;
        private PyObject realStdin, realStdout, realStderr;

        public Task(Application app) {
            this(app, InputType.TYPE_CLASS_TEXT);
        }

        public Task(Application app, int inputType) {
            super(app);
            this.inputType = inputType;
            if (inputType != InputType.TYPE_NULL) {
                realStdin = sys.get("stdin");
                stdin = console.callAttr("ConsoleInputStream", this);
            }

            realStdout = sys.get("stdout");
            realStderr = sys.get("stderr");
            stdout = redirectOutput(realStdout, this::output);
            stderr = redirectOutput(realStderr, this::outputError);
        }

        private PyObject redirectOutput(PyObject stream, OutputFunction func) {
            return console.callAttr("ConsoleOutputStream", stream, func);
        }

        private interface OutputFunction {
            void output(CharSequence text);
        }

        public void resumeStreams() {
            if (stdin != null) {
                sys.put("stdin", stdin);
            }
            sys.put("stdout", stdout);
            sys.put("stderr", stderr);
        }

        public void pauseStreams() {
            if (realStdin != null) {
                sys.put("stdin", realStdin);
            }
            sys.put("stdout", realStdout);
            sys.put("stderr", realStderr);
        }

        @SuppressWarnings("unused")  // Called from Python
        public void onInputState(boolean blocked) {
            if (blocked) {
                inputEnabled.postValue(true);
            }
        }

        @Override public void onInput(String text) {
            if (text != null) {
                // Messages which are empty (or only consist of newlines) will not be logged.
                Log.i("python.stdin", text.equals("\n") ? " " : text);
            }
            stdin.callAttr("on_input", text);
        }

        @Override protected void onCleared() {
            super.onCleared();
            if (stdin != null) {
                onInput(null);  // Signals EOF
            }
        }
    }

}
