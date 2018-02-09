package com.chaquo.python.demo;

import android.os.*;
import android.text.style.*;
import android.util.*;
import com.chaquo.python.*;


/** Redirects Python's stdin, stdout and stderr to connect to the user interface. */
public abstract class PythonConsoleActivity extends ConsoleActivity {

    // TODO: maybe a fragment would be a cleaner way to achieve this.
    protected static class State extends ConsoleActivity.State {
        Python py;
        PyObject sys;
        PyObject prevStdin, prevStdout, prevStderr;
        PyObject stdin, stdout, stderr;

        public State() {
            py = Python.getInstance();
            sys = py.getModule("sys");
            prevStdin = sys.get("stdin");
            prevStdout = sys.get("stdout");
            prevStderr = sys.get("stderr");

            PyObject utils = py.getModule("chaquopy.utils.console");
            stdin = utils.callAttr("ConsoleInputStream", (Object) null);
            stdout = utils.callAttr("ConsoleOutputStream", null, "output", prevStdout);
            stderr = utils.callAttr("ConsoleOutputStream", null, "outputStderr", prevStderr);
        }

        public void start(PythonConsoleActivity activity) {
            stdin.put("activity", activity);
            stdout.put("activity", activity);
            stderr.put("activity", activity);
            sys.put("stdout", stdout);
            sys.put("stderr", stderr);
            sys.put("stdin", stdin);
        }

        public void stop() {
            sys.put("stdout", prevStdout);
            sys.put("stderr", prevStderr);
            sys.put("stdin", prevStdin);
        }
    }
    protected State state;

    protected State initState() {
        return new State();
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        state = (State) super.state;
    }

    @Override
    protected void onStart() {
        super.onStart();
        state.start(this);
    }

    // FIXME should retain streams in state and restore them if we're started again. stdin should
    // return EOF only if we're really being destroyed. But how can we know that? If isFinishing
    // isn't good enough, might need to use a retained fragment. Worried about leaving threads
    // or streams behind in some circumstances.
    //
    // FIXME restoring stdin may cause background thread to block permanently. We can't give
    // enough isolation between activities here without starting a separate process. Add a comment
    // at the top to explain this.
    @Override
    protected void onStop() {
        super.onStop();
        state.stop();
    }

    public void outputStderr(CharSequence text) {
        output(text, new ForegroundColorSpan(getResources().getColor(R.color.console_stderr)));
    }

    @Override
    public void onInput(String input) {
        Log.i("python.stdin", input);
        state.stdin.callAttr("on_input", input);
    }

    public void setInputState(final boolean blocked) {
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                onInputState(blocked);
            }
        });
    }

    /** If `blocked` is true, the background thread is blocked waiting for input. If it's false,
     * the thread has become unblocked. */
    public void onInputState(boolean blocked) {}

}
