package com.chaquo.python.demo;

import android.os.*;
import android.view.*;
import android.widget.*;
import com.chaquo.python.*;


public class ReplActivity extends ConsoleActivity {
    private EditText etInput;
    private PyObject interp;

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

        Python py = Python.getInstance();
        interp = py.getModule("code").callAttr("InteractiveInterpreter");
        PyObject sys = py.getModule("sys");
        append("Python " + sys.get("version") + "\n");
    }

    private void onInput() {
        String input = etInput.getText().toString().trim();
        if (input.isEmpty()) return;
        append(getString(R.string.prompt) + etInput.getText() + "\n");
        etInput.setText("");
        exec(input);
    }

    private void exec(String input) {
        interp.callAttr("runsource", input);
    }

    protected void scroll(int direction) {
        super.scroll(direction);
        etInput.requestFocus();
    }

}
