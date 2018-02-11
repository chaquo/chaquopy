package com.chaquo.python.demo;

import android.os.*;
import com.chaquo.python.*;


public class ReplActivity extends ConsoleActivity {

    protected static class State extends ConsoleActivity.State {
        PyObject console;
        boolean more = false;

        public State(ReplActivity activity) {
            PyObject locals = activity.py.getBuiltins().callAttr("dict", new Kwarg("context", activity));
            console = activity.py.getModule("code").callAttr("InteractiveConsole", locals);
        }
    }
    private State state;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        state = (State) ((ConsoleActivity)this).state;

        setInputVisible(true);
    }

    @Override
    protected void onRestoreInstanceState(Bundle savedInstanceState) {
        super.onRestoreInstanceState(savedInstanceState);
        if (getLastCustomNonConfigurationInstance() == null) {
            // Don't restore the scrollback if the Python InteractiveConsole object can't be
            // restored as well (saw this happen once).
            tvBuffer.setText("");
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (tvBuffer.getText().length() == 0) {
            PyObject sys = py.getModule("sys");
            append(String.format("Python %s on %s\n", sys.get("version"), sys.get("platform")));
            append(getString(R.string.repl_banner) + "\n");
            append(getPrompt());
            input("from java import *\n");
        }
    }

    @Override
    protected State initState() {
        return new State(this);
    }

    public void onBackPressed() {
        moveTaskToBack(true);
    }

    @Override public void onInput(String input) {
        if (input.endsWith("\n")) {
            input = input.substring(0, input.length() - 1);
        }
        state.more = state.console.callAttr("push", input).toJava(Boolean.class);
        append(getPrompt());
    }

    private String getPrompt() {
        return getString(state.more ? R.string.ps2 : R.string.ps1);
    }

}
