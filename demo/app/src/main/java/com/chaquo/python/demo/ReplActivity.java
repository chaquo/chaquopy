package com.chaquo.python.demo;

import android.os.*;
import android.support.v7.app.*;
import android.view.*;
import android.widget.*;

import com.chaquo.python.*;

public class ReplActivity extends AppCompatActivity {

    private ScrollView svBuffer;
    private TextView tvBuffer;
    private EditText etInput;

    private PyObject interp, stdout;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_repl);

        svBuffer = (ScrollView) findViewById(R.id.svBuffer);
        tvBuffer = (TextView) findViewById(R.id.tvBuffer);
        etInput = (EditText) findViewById(R.id.etInput);
        etInput.setOnEditorActionListener(new TextView.OnEditorActionListener() {
            @Override
            public boolean onEditorAction(TextView v, int actionId, KeyEvent event) {
                onInput();
                return true;
            }
        });

        // For when keyboard is shown
        svBuffer.getViewTreeObserver().addOnGlobalLayoutListener(new ViewTreeObserver.OnGlobalLayoutListener() {
            @Override
            public void onGlobalLayout() {
                scrollDown();
            }
        });

        Python py = Python.getInstance();
        interp = py.getModule("code").callAttr("InteractiveInterpreter");
        PyObject sys = py.getModule("sys");
        stdout = py.getModule("StringIO").callAttr("StringIO");
        sys.put("stdout", stdout);
        sys.put("stderr", stdout);
        append("Python " + sys.get("version"));
    }

    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        MenuInflater mi = getMenuInflater();
        mi.inflate(R.menu.top_bottom, menu);
        return true;
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        switch (item.getItemId()) {
            case R.id.menu_top: {
                svBuffer.fullScroll(View.FOCUS_UP);
            } break;

            case R.id.menu_bottom: {
                svBuffer.fullScroll(View.FOCUS_DOWN);
            } break;

            default: return false;
        }
        return true;
    }

    private void onInput() {
        String input = etInput.getText().toString().trim();
        if (input.isEmpty()) return;

        append(getString(R.string.prompt) +
               etInput.getText());
        etInput.setText("");

        // TODO: use sys.ps1
        // TODO: multi-line input (InteractiveConsole)
        // TODO: make text copyable
        // TODO: input history (On-screen arrow buttons? See what other Python REPL apps do.)
        append(exec(input));
        scrollDown();
    }

    private void append(String text) {
        if (text.endsWith("\n")) {
            text = text.substring(0, text.length() - 1);
        }
        if (text.length() == 0) return;

        if (tvBuffer.getText().length() > 0) {
            tvBuffer.append("\n");
        }
        tvBuffer.append(text);
    }

    private String exec(String input) {
        interp.callAttr("runsource", input);
        String result = stdout.callAttr("getvalue").toJava(String.class);
        stdout.callAttr("seek", 0);
        stdout.callAttr("truncate", 0);
        return result;
    }

    private void scrollDown() {
        svBuffer.post(new Runnable() {
            @Override
            public void run() {
                svBuffer.fullScroll(View.FOCUS_DOWN);
                etInput.requestFocus();
            }
        });
    }

}
