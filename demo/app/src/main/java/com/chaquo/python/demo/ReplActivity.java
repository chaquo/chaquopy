package com.chaquo.python.demo;

import android.os.*;
import android.view.*;
import android.widget.*;
import com.chaquo.python.*;


public class ReplActivity extends ConsoleActivity {

    private EditText etInput;

    protected static class State extends ConsoleActivity.State {
        PyObject interp;

        public State(ReplActivity activity) {
            Python py = Python.getInstance();
            PyObject locals = py.getBuiltins().callAttr("dict", new Kwarg("context", activity));
            interp = py.getModule("code").callAttr("InteractiveInterpreter", locals);
        }
    }
    private State state;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        setContentView(R.layout.activity_repl);
        super.onCreate(savedInstanceState);

        etInput = (EditText) findViewById(R.id.etInput);
        etInput.setOnEditorActionListener(new TextView.OnEditorActionListener() {
            @Override
            public boolean onEditorAction(TextView v, int actionId, KeyEvent event) {
                String input = etInput.getText().toString().trim();
                if (! input.isEmpty()) {
                    etInput.setText("");
                    exec(input);
                }
                return true;
            }
        });

        state = (State) ((ConsoleActivity)this).state;
        if (savedInstanceState == null) {
            Python py = Python.getInstance();
            PyObject sys = py.getModule("sys");
            append("Python " + sys.get("version") + "\n" +
                   getString(R.string.repl_banner) + "\n");
            exec("from java import *");
        }
    }

    @Override
    protected State initState() {
        return new State(this);
    }

    private void exec(String input) {
        append(getString(R.string.repl_prompt) + input + "\n");
        boolean needMore = state.interp.callAttr("runsource", input).toJava(Boolean.class);
        if (needMore) {
            append("Error: incomplete input\n");  // TODO #5205
        }
    }

    protected void scroll(int direction) {
        super.scroll(direction);
        etInput.requestFocus();
    }

}
