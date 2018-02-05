package com.chaquo.python.demo;

import android.os.*;
import android.util.*;
import com.chaquo.python.*;


public class ReplActivity extends PythonConsoleActivity {
/* FIXME
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
        setInputEnabled(true);
    }

    @Override
    protected State initState() {
        return new State(this);
    }


    @Override
    protected void onResume() {
        super.onResume();
        // FIXME should be in run()? Is text check still necessary? See recently closed issue.
        if (tvBuffer.getText().length() == 0) {
            PyObject sys = py.getModule("sys");
            output(String.format("Python %s on %s\n", sys.get("version"), sys.get("platform")));
            output(getString(R.string.repl_banner) + "\n");
            push("from java import *");
        }
    }
    */

    @Override
    protected void run() {
        // FIXME
    }

    @Override
    protected void onInput(String input) {
        // FIXME
    }

    /*FIXME

    public void onBackPressed() {
        moveTaskToBack(true);
    }

    private void push(String input) {
        String prompt = getPrompt();
        FIXME;
        Log.i("ReplActivity", spannableInput.toString());
        output(spannableInput);

        state.more = state.console.callAttr("push", input).toJava(Boolean.class);
        etInput.setHint(getPrompt());
    }

    private String getPrompt() {
        return getString(state.more ? R.string.ps2 : R.string.ps1);
    }
*/
}
