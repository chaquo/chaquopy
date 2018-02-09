package com.chaquo.python.demo;

import android.os.*;
import android.support.v7.app.*;
import android.text.*;
import android.util.*;
import android.view.*;
import android.widget.*;
import com.chaquo.python.*;

public abstract class ConsoleActivity extends AppCompatActivity {

    protected Python py;
    protected ScrollView svOutput;  // FIXME private
    protected TextView tvOutput;    // FIXME private

    protected static class State {
        boolean pendingNewline = false;  // Prevent empty line at bottom of screen
    }
    protected State state;

    private PyObject prevStdout, prevStderr;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        py = Python.getInstance();
        state = (State) getLastCustomNonConfigurationInstance();
        if (state == null) {
            state = initState();
        }

        svOutput = (ScrollView) findViewById(R.id.svBuffer);
        svOutput.getViewTreeObserver().addOnScrollChangedListener(
            new ViewTreeObserver.OnScrollChangedListener() {
                @Override public void onScrollChanged() { saveScroll(); }
            });

        tvOutput = (TextView) findViewById(R.id.tvBuffer);
        if (Build.VERSION.SDK_INT >= 23) {
            tvOutput.setBreakStrategy(Layout.BREAK_STRATEGY_SIMPLE);
        }
    }

    protected State initState() {
        return new State();
    }

    @Override
    public Object onRetainCustomNonConfigurationInstance() {
        return state;
    }

    @Override
    protected void onStart() {
        super.onStart();
        PyObject utils = py.getModule("chaquopy.demo.utils");
        PyObject JavaTeeOutputStream = utils.get("JavaTeeOutputStream");
        PyObject sys = py.getModule("sys");
        prevStdout = sys.get("stdout");
        prevStderr = sys.get("stderr");
        sys.put("stdout", JavaTeeOutputStream.call(prevStdout, this, "output"));
        sys.put("stderr", JavaTeeOutputStream.call(prevStderr, this, "output"));
    }

    @Override
    protected void onStop() {
        super.onStop();
        PyObject sys = py.getModule("sys");
        sys.put("stdout", prevStdout);
        sys.put("stderr", prevStderr);
    }

    // After a rotation or a keyboard show/hide, a ScrollView will restore the previous pixel scroll
    // position. However, due to re-wrapping, this may result in a completely different piece of
    // text being visible. FIXME We'll try to maintain the text position of the top line, unless the view
    // is scrolled to the bottom, in which case we'll maintain that.
    private void saveScroll() {
        Spannable s = (Spannable) tvOutput.getText();
        if (Selection.getSelectionStart(s) != Selection.getSelectionEnd(s)) {
            return;  // Don't interfere with an actual selection
        }
        int cursorPos;
        if (isScrolledToBottom()) {
            cursorPos = s.length();
        } else {
            Layout layout = tvOutput.getLayout();
            cursorPos = layout.getLineStart(layout.getLineForVertical(svOutput.getScrollY()));
        }
        Selection.setSelection(s, cursorPos);
    }

    private boolean isScrolledToBottom() {
        int visibleHeight = (svOutput.getHeight() - svOutput.getPaddingTop() -
                             svOutput.getPaddingBottom());
        int maxScroll = Math.max(0, tvOutput.getHeight() - visibleHeight);
        return (svOutput.getScrollY() >= maxScroll);
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

    public void output(final CharSequence text) {
        if (text.length() == 0) return;
        runOnUiThread(new Runnable() {
            @Override public void run() {
                boolean atBottom = isScrolledToBottom();
                Log.d("output", text.toString() + ", height=" + svOutput.getHeight());

                if (state.pendingNewline) {
                    tvOutput.append("\n");
                    state.pendingNewline = false;
                }
                if (text.charAt(text.length() - 1) == '\n') {
                    tvOutput.append(text.subSequence(0, text.length() - 1));
                    state.pendingNewline = true;
                } else {
                    tvOutput.append(text);
                }

                if (atBottom) {
                    scroll(View.FOCUS_DOWN);
                }
            }
        });
    }

    public void scroll(final int direction) {
        // post to give the TextView a chance to update its dimensions if the text has just changed.
        svOutput.post(new Runnable() {
            @Override public void run() {
                svOutput.fullScroll(direction);
                Log.d("scroll", "height=" + svOutput.getHeight());
            }
        });
    }

}
