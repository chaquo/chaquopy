package com.chaquo.python.demo;

import android.os.*;
import android.support.v7.app.*;
import android.view.*;
import android.widget.*;

import com.chaquo.python.*;

public class MainActivity extends AppCompatActivity {

    private ScrollView svBuffer;
    private TextView tvBuffer;
    private EditText etInput;

    private PyObject interp, stdout;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

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
    }

    private void onInput() {
        String input = etInput.getText().toString().trim();
        if (input.isEmpty()) return;

        CharSequence text = tvBuffer.getText();
        if (text.length() > 0  &&  text.charAt(text.length() - 1) != '\n') {
            tvBuffer.append("\n");
        }
        tvBuffer.append(getString(R.string.prompt));
        tvBuffer.append(etInput.getText());
        tvBuffer.append("\n");
        etInput.setText("");

        // TODO: multi-line input
        // TODO: input history (On-screen arrow buttons? See what other Python REPL apps do.)
        tvBuffer.append(exec(input));
        scrollDown();
    }

    private String exec(String input) {
        interp.callAttr("runsource", input);
        String result = stdout.callAttr("getvalue").toJava();
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
