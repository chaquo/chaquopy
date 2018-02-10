package com.chaquo.python.demo;

import android.annotation.*;
import android.os.*;
import android.support.v7.app.*;
import android.text.*;
import android.text.style.*;
import android.view.*;
import android.widget.*;
import com.chaquo.python.*;


public abstract class ConsoleActivity extends AppCompatActivity
implements ViewTreeObserver.OnGlobalLayoutListener {

    protected Python py;
    private ScrollView svBuffer;
    protected TextView tvBuffer;    // FIXME private
    private int outputWidth = 0, outputHeight = 0;

    protected static class State {
        boolean pendingNewline = false;  // Prevent empty line at bottom of screen
        int scrollChar = 0;              // Character offset of the top visible line.
        int scrollAdjust = 0;            // Pixels by which that line is scrolled above the top
                                         //   (prevents movement when keyboard hidden/shown).
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

        svBuffer = (ScrollView) findViewById(R.id.svBuffer);
        svBuffer.getViewTreeObserver().addOnScrollChangedListener(
            new ViewTreeObserver.OnScrollChangedListener() {
                @Override public void onScrollChanged() { saveScroll(); }
            });

        svBuffer.getViewTreeObserver().addOnGlobalLayoutListener(this);

        tvBuffer = (TextView) findViewById(R.id.tvBuffer);
        if (Build.VERSION.SDK_INT >= 23) {
            tvBuffer.setBreakStrategy(Layout.BREAK_STRATEGY_SIMPLE);
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
        sys.put("stdout", JavaTeeOutputStream.call(prevStdout, this, "append"));
        sys.put("stderr", JavaTeeOutputStream.call(prevStderr, this, "appendStderr"));
    }

    // This callback is triggered by numerous events, all of which occur after onResume, at a time
    // when we have completed layout. We're only interested if the append view size has been
    // initialized or changed, and we want to avoid adjusting the scroll at other times because it
    // can interfere with auto-scrolling.
    @Override public void onGlobalLayout() {
        if (outputWidth != svBuffer.getWidth() || outputHeight != svBuffer.getHeight()) {
            outputWidth = svBuffer.getWidth();
            outputHeight = svBuffer.getHeight();
            restoreScroll();
        }
    }

    @Override
    protected void onStop() {
        super.onStop();
        PyObject sys = py.getModule("sys");
        sys.put("stdout", prevStdout);
        sys.put("stderr", prevStderr);
    }

    // After a rotation, a ScrollView will restore the previous pixel scroll position. However, due
    // to re-wrapping, this may result in a completely different piece of text being visible. We'll
    // try to maintain the text position of the top line, unless the view is scrolled to the bottom,
    // in which case we'll maintain that. Maintaining the bottom line will also cause a scroll
    // adjustment when the keyboard's hidden or shown.
    private void saveScroll() {
        if (isScrolledToBottom()) {
            state.scrollChar = tvBuffer.getText().length();
            state.scrollAdjust = 0;
        } else {
            int scrollY = svBuffer.getScrollY();
            Layout layout = tvBuffer.getLayout();
            int line = layout.getLineForVertical(scrollY);
            state.scrollChar = layout.getLineStart(line);
            state.scrollAdjust = scrollY - layout.getLineTop(line);
        }
    }

    private void restoreScroll() {
        removeCursor();
        Layout layout = tvBuffer.getLayout();
        int line = layout.getLineForOffset(state.scrollChar);
        svBuffer.scrollTo(0, layout.getLineTop(line) + state.scrollAdjust);
    }

    private boolean isScrolledToBottom() {
        int visibleHeight = (svBuffer.getHeight() - svBuffer.getPaddingTop() -
                             svBuffer.getPaddingBottom());
        int maxScroll = Math.max(0, tvBuffer.getHeight() - visibleHeight);
        return (svBuffer.getScrollY() >= maxScroll);
    }

    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        MenuInflater mi = getMenuInflater();
        mi.inflate(R.menu.top_bottom, menu);
        return true;
    }

    @Override public boolean onOptionsItemSelected(MenuItem item) {
        switch (item.getItemId()) {
            case R.id.menu_top: {
                handler.sendEmptyMessage(SCROLL_TOP);
            } break;

            case R.id.menu_bottom: {
                handler.sendEmptyMessage(SCROLL_BOTTOM);
            } break;

            default: return false;
        }
        return true;
    }

    @SuppressWarnings("unused")  // Passed to Python above
    public void appendStderr(CharSequence text) {
        int color = getResources().getColor(R.color.console_stderr);
        append(span(text, new ForegroundColorSpan(color)));
    }

    private static Spannable span(CharSequence text, Object... spans) {
        Spannable spanText = new SpannableStringBuilder(text);
        for (Object span : spans) {
            spanText.setSpan(span, 0, text.length(), 0);
        }
        return spanText;
    }

    public void append(CharSequence text) { append(text, false); }

    public void append(final CharSequence text, final boolean forceScroll) {
        if (text.length() == 0) return;
        runOnUiThread(new Runnable() {
            @Override public void run() {
                removeCursor();
                if (state.pendingNewline) {
                    tvBuffer.append("\n");
                    state.pendingNewline = false;
                }
                if (text.charAt(text.length() - 1) == '\n') {
                    tvBuffer.append(text.subSequence(0, text.length() - 1));
                    state.pendingNewline = true;
                } else {
                    tvBuffer.append(text);
                }

                // If the append has caused the TextView to get taller, that won't be reflected by
                // getHeight until after the next layout pass, which has now been scheduled. So
                // isScrolledToBottom is safe here, but scrollTo needs to be posted so it runs
                // after layout.
                if (forceScroll || isScrolledToBottom()) {
                    handler.sendEmptyMessage(SCROLL_BOTTOM);
                }
            }
        });
    }

    private static final int SCROLL_TOP = 0, SCROLL_BOTTOM = 1;

    @SuppressLint("HandlerLeak")  // No delayed messages are used.
    Handler handler = new Handler() {
        @Override public void handleMessage(Message msg) {
            switch (msg.what) {
                case SCROLL_TOP:
                    scrollTo(0);
                    removeMessages(SCROLL_BOTTOM);  // Prevent pending auto-scroll.
                    break;
                case SCROLL_BOTTOM:
                    scrollTo(tvBuffer.getHeight());
                    break;
                default: throw new Error(msg.toString());
            }
        }

        // Don't use smooth scroll, because if an output call happens while it's animating towards
        // the bottom, isScrolledToBottom will believe we've left the bottom and auto-scrolling will
        // stop. Don't use fullScroll either, because not only does it use smooth scroll, it also
        // grabs focus.
        public void scrollTo(int y) {
            svBuffer.scrollTo(0, y);
        }
    };

    // Because we've set textIsSelectable, the TextView will create an invisible cursor (i.e. a
    // zero-length selection) during startup, and re-create it if necessary whenever the user taps
    // on the view. When a TextView is focused and it has a cursor, it will adjust its containing
    // ScrollView whenever the text changes in an attempt to keep the cursor on-screen.
    // textIsSelectable implies focusable, so if there are no other focusable views in the layout,
    // then it will always be focused.
    //
    // This interferes with our own scroll control, so we'll remove the cursor before we try
    // from happening. Non-zero-length selections are left untouched.
    private void removeCursor() {
        int selStart = tvBuffer.getSelectionStart();
        int selEnd = tvBuffer.getSelectionEnd();
        if (selStart != -1 && selStart == selEnd) {
            Selection.removeSelection((Spannable) tvBuffer.getText());
        }
    }

}
