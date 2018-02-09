package com.chaquo.python.demo;

import android.os.*;
import com.chaquo.python.*;


public class ReplActivity extends PythonConsoleActivity {
    protected static class State extends PythonConsoleActivity.State {
        PyObject console;
        boolean initialized = false;

        public State(ReplActivity activity) {
            console = (py.getModule("chaquopy.demo.repl")
                       .callAttr("AndroidConsole", activity));
        }
    }
    protected State state;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        state = (State) super.state;
        setInputEnabled(true);
    }

    @Override
    protected State initState() { return new State(this); }

    @Override
    public void run() {
        state.console.callAttr("interact");
    }


    // FIXME put setInputEnabled in ConsoleActivity (passing either true or false will show input box).
    // Buffer input lines if input() is called while not enabled. Then move this to run(), which should end up as the only function
    // in this activity.
    // FIXME possible problem with this is keyboard will disappear when text box is disabled.
    @Override
    public void onInputState(boolean blocked) {
        if (blocked && !state.initialized) {
            input("from java import *\n");
            state.initialized = true;
        }
    }
}
