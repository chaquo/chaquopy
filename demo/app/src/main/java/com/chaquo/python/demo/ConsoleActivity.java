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
        int scrollChar = 0;              // Character offset of the top visible line.
        int scrollAdjust = 0;            // Pixels by which that line is scrolled above the top
                                         // (prevents movement when keyboard hidden/shown).
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

        // Triggered by various events, including:
        //   * After onResume, while the UI is being laid out (possibly multiple times).
        //   * Keyboard is shown or hidden.
        //   * Text selection toolbar appears or disappears (on some Android versions).
        svOutput.getViewTreeObserver().addOnGlobalLayoutListener(new ViewTreeObserver.OnGlobalLayoutListener() {
            @Override public void onGlobalLayout() {
                restoreScroll();
            }
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
    // text being visible. We'll try to maintain the text position of the top line, unless the view
    // is scrolled to the bottom, in which case we'll maintain that.
    private void saveScroll() {
        if (isScrolledToBottom()) {
            state.scrollChar = tvOutput.getText().length();
            state.scrollAdjust = 0;
        } else {
            int scrollY = svOutput.getScrollY();
            Layout layout = tvOutput.getLayout();
            int line = layout.getLineForVertical(scrollY);
            state.scrollChar = layout.getLineStart(line);
            state.scrollAdjust = scrollY - layout.getLineTop(line);
        }
    }

    private void restoreScroll() {
        // Because we've set textIsSelectable, the TextView will create an invisible cursor (i.e. a
        // zero-length selection) during startup, and re-create it if necessary whenever the user
        // taps on the view. When a TextView is focused and it has a cursor, it will adjust its xxxxxxxx
        // containing ScrollView to keep the cursor on-screen. textIsSelectable implies focusable,
        // so if there are no other focusable views in the layout, then it will always be focused.
        //
        // This interferes with our own scroll control, so we'll remove the cursor to stop it
        // from happening. Non-zero-length selections are left untouched.
        int selStart = tvOutput.getSelectionStart();
        int selEnd = tvOutput.getSelectionEnd();
        if (selStart != -1 && selStart == selEnd) {
            Selection.removeSelection((Spannable) tvOutput.getText());
        }

        Layout layout = tvOutput.getLayout();
        int line = layout.getLineForOffset(state.scrollChar);
        svOutput.scrollTo(0, layout.getLineTop(line) + state.scrollAdjust);
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
                Log.i("output", text.toString() + ", atBottom=" + atBottom);

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
            }
        });
    }

}
