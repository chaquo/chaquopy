package com.chaquo.python.demo;

import android.os.*;
import android.support.v7.app.*;
import android.text.*;
import android.util.*;
import android.view.*;
import android.widget.*;
import com.chaquo.python.*;
import java.util.*;

public abstract class ConsoleActivity extends AppCompatActivity {

    protected Python py;
    protected ScrollView svBuffer;
    protected TextView tvBuffer;

    protected static class State {
        boolean pendingNewline = false;  // Prevent empty line at bottom of screen
        boolean scrolledToBottom = false;
    }
    protected State state;

    private PyObject prevStdout, prevStderr;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        py = Python.getInstance();
        svBuffer = (ScrollView) findViewById(R.id.svBuffer);
        tvBuffer = (TextView) findViewById(R.id.tvBuffer);
        if (Build.VERSION.SDK_INT >= 23) {
            tvBuffer.setBreakStrategy(Layout.BREAK_STRATEGY_SIMPLE);
        }

        state = (State) getLastCustomNonConfigurationInstance();
        if (state == null) {
            state = initState();
        }

        svBuffer.getViewTreeObserver().addOnScrollChangedListener(new ViewTreeObserver.OnScrollChangedListener() {
            @Override
            public void onScrollChanged() {
                state.scrolledToBottom = isScrolledToBottom();
            }
        });

        // Triggered when the keyboard is hidden or shown. Also triggered by the text selection
        // toolbar appearing and disappearing, on Android versions which use it.
        svBuffer.getViewTreeObserver().addOnGlobalLayoutListener(new ViewTreeObserver.OnGlobalLayoutListener() {
            @Override
            public void onGlobalLayout() {
                adjustScroll();
            }
        });
    }

    protected State initState() {
        return new State();
    }

    @Override
    protected void onRestoreInstanceState(Bundle savedInstanceState) {
        // Don't restore the REPL UI scrollback if the Python InteractiveConsole object can't be
        // restored as well (saw this happen once).
        if (getLastCustomNonConfigurationInstance() != null) {
            super.onRestoreInstanceState(savedInstanceState);
        }
    }

    @Override
    protected void onStart() {
        super.onStart();
        adjustScroll();  // Necessary after a screen rotation

        PyObject utils = py.getModule("chaquopy.demo.utils");
        PyObject JavaTeeOutputStream = utils.get("JavaTeeOutputStream");
        PyObject sys = py.getModule("sys");
        prevStdout = sys.get("stdout");
        prevStderr = sys.get("stderr");
        sys.put("stdout", JavaTeeOutputStream.call(prevStdout, this, "append"));
        sys.put("stderr", JavaTeeOutputStream.call(prevStderr, this, "append"));
    }

    @Override
    protected void onStop() {
        super.onStop();
        PyObject sys = py.getModule("sys");
        sys.put("stdout", prevStdout);
        sys.put("stderr", prevStderr);
    }

    private void adjustScroll() {
        if (state.scrolledToBottom  &&  ! isScrolledToBottom()) {
            scroll(View.FOCUS_DOWN);
        }
    }

    private boolean isScrolledToBottom() {
        int svBufferHeight = (svBuffer.getHeight() -
        svBuffer.getPaddingTop() -
        svBuffer.getPaddingBottom());
        int maxScroll = Math.max(0, tvBuffer.getHeight() - svBufferHeight);
        return (svBuffer.getScrollY() >= maxScroll);
    }

    @Override
    public Object onRetainCustomNonConfigurationInstance() {
        return state;
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

    public void append(CharSequence text) {
        if (text.length() == 0) return;
        final List<CharSequence> fragments = new ArrayList<>();
        if (state.pendingNewline) {
            fragments.add("\n");
            state.pendingNewline = false;
        }
        if (text.charAt(text.length() - 1) == '\n') {
            fragments.add(text.subSequence(0, text.length() - 1));
            state.pendingNewline = true;
        } else {
            fragments.add(text);
        }
        
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                for (CharSequence frag : fragments) {
                    tvBuffer.append(frag);
                }
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
