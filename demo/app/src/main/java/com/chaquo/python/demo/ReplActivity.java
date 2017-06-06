package com.chaquo.python.demo;

import android.os.*;
import android.view.*;
import android.widget.*;
import com.chaquo.python.*;


public class ReplActivity extends ConsoleActivity {

    private EditText etInput;

    protected static class State extends ConsoleActivity.State {
        PyObject interp;

        public State() {
            Python py = Python.getInstance();
            interp = py.getModule("code").callAttr("InteractiveInterpreter");
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
                onInput();
                return true;
            }
        });

        if (savedInstanceState == null) {
            Python py = Python.getInstance();
            PyObject sys = py.getModule("sys");
            append("Python " + sys.get("version") + "\n");
        }

        state = (State) ((ConsoleActivity)this).state;
    }

    @Override
    protected State initState() {
        return new State();
    }

    private void onInput() {
        String input = etInput.getText().toString().trim();
        if (input.isEmpty()) return;
        append(getString(R.string.prompt) + etInput.getText() + "\n");
        etInput.setText("");
        exec(input);
    }

    private void exec(String input) {
        state.interp.callAttr("runsource", input);
    }

    protected void scroll(int direction) {
        super.scroll(direction);
        etInput.requestFocus();
    }

}
