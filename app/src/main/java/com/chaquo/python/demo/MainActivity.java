package com.chaquo.python.demo;

import android.os.*;
import android.support.v7.app.*;
import android.view.*;
import android.widget.*;

public class MainActivity extends AppCompatActivity {

    private Repl repl = Repl.getInstance();

    private ScrollView svBuffer;
    private TextView tvBuffer;
    private EditText etInput;

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

        repl.start();
    }

    private void onInput() {
        String input = etInput.getText().toString().trim();
        if (input.isEmpty()) return;

        if (tvBuffer.getText().length() > 0) {
            tvBuffer.append("\n");
        }
        tvBuffer.append(getString(R.string.prompt));
        tvBuffer.append(etInput.getText());
        tvBuffer.append("\n");
        etInput.setText("");

        tvBuffer.append(repl.eval(input));
        scrollDown();
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

    @Override
    protected void onDestroy() {
        repl.stop();
        super.onDestroy();
    }

}
