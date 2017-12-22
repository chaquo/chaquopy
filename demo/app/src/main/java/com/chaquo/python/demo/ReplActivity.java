package com.chaquo.python.demo;

import android.graphics.*;
import android.os.*;
import android.text.*;
import android.text.style.*;
import android.view.*;
import android.view.inputmethod.*;
import android.widget.*;
import com.chaquo.python.*;


public class ReplActivity extends ConsoleActivity {

    private EditText etInput;

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
        setContentView(R.layout.activity_repl);
        super.onCreate(savedInstanceState);
        state = (State) ((ConsoleActivity)this).state;

        etInput = (EditText) findViewById(R.id.etInput);
        etInput.setHint(getPrompt());
        etInput.addTextChangedListener(new TextWatcher() {
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            public void onTextChanged(CharSequence s, int start, int before, int count) {}

            // Strip formatting from pasted text.
            @Override
            public void afterTextChanged(Editable e) {
                for (CharacterStyle cs : e.getSpans(0, e.length(), CharacterStyle.class)) {
                    e.removeSpan(cs);
                }
            }
        });
        etInput.setOnEditorActionListener(new TextView.OnEditorActionListener() {
            @Override
            public boolean onEditorAction(TextView v, int actionId, KeyEvent event) {
                if (actionId == EditorInfo.IME_ACTION_DONE ||
                    (event != null && event.getAction() == KeyEvent.ACTION_DOWN)) {
                    String input = etInput.getText().toString();
                    etInput.setText("");
                    push(input);
                    return true;
                }
                return false;
            }
        });

        if (savedInstanceState == null) {
            PyObject sys = py.getModule("sys");
            append(String.format("Python %s on %s\n",sys.get("version"), sys.get("platform")));
            append(getString(R.string.repl_banner) + "\n");
            push("from java import *");
        }
    }

    @Override
    protected State initState() {
        return new State(this);
    }

    public void onBackPressed() {
        moveTaskToBack(true);
    }

    private void push(String input) {
        append(getPrompt());
        SpannableString spannableInput = new SpannableString(input);
        spannableInput.setSpan(new StyleSpan(Typeface.BOLD), 0, input.length(), 0);
        append(spannableInput);
        append("\n");

        state.more = state.console.callAttr("push", input).toJava(Boolean.class);
        etInput.setHint(getPrompt());
    }

    private String getPrompt() {
        return getString(state.more ? R.string.ps2 : R.string.ps1);
    }

    protected void scroll(int direction) {
        super.scroll(direction);
        etInput.requestFocus();
    }

}
