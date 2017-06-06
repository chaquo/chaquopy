package com.chaquo.python.demo;

import android.os.*;
import android.support.v7.app.*;
import android.util.*;
import android.view.*;
import android.widget.*;
import com.chaquo.python.*;

public class ConsoleActivity extends AppCompatActivity {

    private ScrollView svBuffer;
    private TextView tvBuffer;
    private boolean pendingNewline = false;  // Prevent empty line at bottom of screen

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        svBuffer = (ScrollView) findViewById(R.id.svBuffer);
        tvBuffer = (TextView) findViewById(R.id.tvBuffer);

        // For when keyboard is shown
        svBuffer.getViewTreeObserver().addOnGlobalLayoutListener(new ViewTreeObserver.OnGlobalLayoutListener() {
            @Override
            public void onGlobalLayout() {
                scroll(View.FOCUS_DOWN);
            }
        });

        Python py = Python.getInstance();
        PyObject console_activity = py.getModule("console_activity");
        PyObject stream = console_activity.callAttr("ForwardingOutputStream", this, "append");
        PyObject sys = py.getModule("sys");
        sys.put("stdout", stream);
        sys.put("stderr", stream);
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
                scroll(View.FOCUS_UP);
            } break;

            case R.id.menu_bottom: {
                scroll(View.FOCUS_DOWN);
            } break;

            default: return false;
        }
        return true;
    }

    // Used in console_activity.py
    @SuppressWarnings("unused")
    public void append(String text) {
        if (text.length() == 0) return;

        if (pendingNewline) {
            text = "\n" + text;
            pendingNewline = false;
        }
        if (text.endsWith("\n")) {
            text = text.substring(0, text.length() - 1);
            pendingNewline = true;
        }
        
        final String appendText = text;
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                tvBuffer.append(appendText);
                svBuffer.post(new Runnable() {
                    @Override
                    public void run() {
                        scroll(View.FOCUS_DOWN);
                    }
                });
            }
        });
    }

    protected void scroll(int direction) {
        svBuffer.fullScroll(direction);
    }

}
