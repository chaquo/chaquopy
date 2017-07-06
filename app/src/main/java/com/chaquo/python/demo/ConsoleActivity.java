package com.chaquo.python.demo;

import android.os.*;
import android.support.v7.app.*;
import android.text.*;
import android.view.*;
import android.widget.*;
import com.chaquo.python.*;
import java.util.*;

public class ConsoleActivity extends AppCompatActivity {

    protected Python py = Python.getInstance();
    protected ScrollView svBuffer;
    protected TextView tvBuffer;

    protected static class State {
        boolean pendingNewline = false;  // Prevent empty line at bottom of screen
        boolean scrolledToBottom = false;
    }
    protected State state;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        svBuffer = (ScrollView) findViewById(R.id.svBuffer);
        tvBuffer = (TextView) findViewById(R.id.tvBuffer);
        if (Build.VERSION.SDK_INT >= 23) {
            tvBuffer.setBreakStrategy(Layout.BREAK_STRATEGY_SIMPLE);
        }

        PyObject console_activity = py.getModule("console_activity");
        PyObject stream = console_activity.callAttr("ForwardingOutputStream", this, "append");
        PyObject sys = py.getModule("sys");
        sys.put("stdout", stream);
        sys.put("stderr", stream);

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
    protected void onResume() {
        super.onResume();
        adjustScroll();  // Necessary after a screen rotation
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
