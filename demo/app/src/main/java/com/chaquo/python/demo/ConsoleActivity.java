package com.chaquo.python.demo;

import android.graphics.*;
import android.os.*;
import android.support.v7.app.*;
import android.text.*;
import android.text.style.*;
import android.view.*;
import android.view.inputmethod.*;
import android.widget.*;

public abstract class ConsoleActivity extends AppCompatActivity {

    protected ScrollView svOutput;
    protected TextView tvOutput;
    protected EditText etInput;

    protected static class State {
        boolean alreadyRun = false;
        boolean pendingNewline = false;  // Prevent empty line at bottom of screen
        public int scrollOffset;         // Character offset within tvOutput
    }
    protected State state;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        state = (State) getLastCustomNonConfigurationInstance();
        if (state == null) {
            state = initState();
        }

        setContentView(R.layout.activity_console);
        onCreateOutput();
        onCreateInput();
    }

    protected State initState() {
        return new State();
    }

    @Override
    public Object onRetainCustomNonConfigurationInstance() {
        return state;
    }

    private void onCreateOutput() {
        svOutput = (ScrollView) findViewById(R.id.svOutput);
        svOutput.getViewTreeObserver().addOnScrollChangedListener(
            new ViewTreeObserver.OnScrollChangedListener() {
                @Override
                public void onScrollChanged() { saveScroll(); }
            });
        svOutput.getViewTreeObserver().addOnGlobalLayoutListener(
            new ViewTreeObserver.OnGlobalLayoutListener() {
                // Triggered by various events, including:
                //   * After onResume, while the UI is being laid out (possibly multiple times).
                //   * Keyboard appears or disappears.
                //   * Text selection toolbar appears or disappears (on some Android versions).
                @Override
                public void onGlobalLayout() {
                    restoreScroll();
                }
            });

        tvOutput = (TextView) findViewById(R.id.tvOutput);
        if (Build.VERSION.SDK_INT >= 23) {
            tvOutput.setBreakStrategy(Layout.BREAK_STRATEGY_SIMPLE);
        }
        tvOutput.setText("", TextView.BufferType.EDITABLE); // FIXME explain why not use XML
        RemoveCursorWatcher.install(tvOutput);
    }

    private void onCreateInput() {
        etInput = (EditText) findViewById(R.id.etInput);

        // Strip formatting from pasted text.
        etInput.addTextChangedListener(new TextWatcher() {
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            public void onTextChanged(CharSequence s, int start, int before, int count) {}
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
                    String input = etInput.getText().toString() + "\n";
                    etInput.setText("");
                    SpannableString spanInput = new SpannableString(input);
                    spanInput.setSpan(new StyleSpan(Typeface.BOLD), 0, input.length(), 0);
                    output(spanInput);
                    onInput(input);
                    return true;
                }
                return false;
            }
        });
    }

    protected void setInputEnabled(boolean enabled) {
        if (enabled) {
            etInput.setVisibility(View.VISIBLE);
            etInput.requestFocus();
        } else {
            etInput.setVisibility(View.GONE);
        }
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

    @Override
    protected void onRestoreInstanceState(Bundle savedInstanceState) {
        super.onRestoreInstanceState(savedInstanceState);

        // FIXME refactor with copy in oncreateoutput
        tvOutput.setText(tvOutput.getText(), TextView.BufferType.EDITABLE); // FIXME explain why not use xml
        RemoveCursorWatcher.install(tvOutput);  // Text object may have been replaced.
    }

    // FIXME explain
    // FIXME explain bufferType in xml
    private static class RemoveCursorWatcher implements SpanWatcher {
        private static RemoveCursorWatcher watcher = new RemoveCursorWatcher();

        public static void install(TextView tv) {
            Spannable text = (Spannable) tv.getText();
            text.setSpan(watcher, 0, 0, Spanned.SPAN_INCLUSIVE_EXCLUSIVE);
            watcher.removeCursor(text);
        }

        @Override
        public void onSpanAdded(Spannable text, Object what, int start, int end) {
            removeCursor(text);
        }

        @Override
        public void onSpanChanged(Spannable text, Object what, int ostart, int oend, int nstart,
                                  int nend) {
            removeCursor(text);
        }

        @Override
        public void onSpanRemoved(Spannable text, Object what, int start, int end) {}

        public void removeCursor(Spannable text) {
            int start = Selection.getSelectionStart(text), end = Selection.getSelectionEnd(text);
            if (start != -1 && start == end) {
                Selection.removeSelection(text);
            }
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (! state.alreadyRun) {
            tvOutput.setText("");  // We may have restored the output from a previous instance.
            new Thread(new Runnable() {
                @Override
                public void run() {
                    ConsoleActivity.this.run();
                }
            }).start();
            state.alreadyRun = true;
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        saveScroll(); // FIXME unnecessary?
    }

    /** Override this method to provide the activity's implementation. It will be called on a
     *  background thread. It can call `output` on any thread to add text to the console output. */
    protected abstract void run();

    /** Called each time the user enters a line of input. The default implementation does nothing.
     * If you override this method, you should also call `setInputEnabled(true)`. */
    protected void onInput(String input) {}

    protected void output(final CharSequence text) {
        if (text.length() == 0) return;
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                boolean atBottom = isScrolledToBottom();

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

                /*FIXME
                if (atBottom) {
                    // Auto-scroll once the TextView has updated its layout.
                    svOutput.post(new Runnable() {
                        @Override
                        public void run() {
                            scroll(View.FOCUS_DOWN);
                        }
                    });
                }
                */
            }
        });
    }

    // After a rotation, svOutput will initially restore the previous pixel scroll position.
    // However, due to re-wrapping, this may result in a completely different piece of text being
    // visible.
    //
    // If etInput is disabled, then tvOutput will be the focused view (textIsSelectable implies
    // focusable). In this case, svOutput will be scrolled again, by the minimum amount necessary to
    // put tvInput's cursor on-screen. (The cursor is invisible, and is located by default at the
    // end, or at the character which was last tapped.)
    private void saveScroll() {
        if (isScrolledToBottom()) {
            state.scrollOffset = tvOutput.getText().length();
        } else {
            Layout layout = tvOutput.getLayout();
            state.scrollOffset =
                layout.getLineStart(layout.getLineForVertical(svOutput.getScrollY()));
        }
    }

    private void restoreScroll() {
        Layout layout = tvOutput.getLayout();
        int scrollY = layout.getLineTop(layout.getLineForOffset(state.scrollOffset));
        svOutput.smoothScrollTo(0, scrollY); // FIXME explain why smooth, or maybe unnecessary now
    }

    private boolean isScrolledToBottom() {
        int visibleHeight = (svOutput.getHeight() - svOutput.getPaddingTop() -
                             svOutput.getPaddingBottom());
        int maxScroll = Math.max(0, tvOutput.getHeight() - visibleHeight);
        return (svOutput.getScrollY() >= maxScroll);
    }

    private void scroll(int direction) {
        svOutput.fullScroll(direction);  // Sets focus to the output.
        if (etInput.getVisibility() == View.VISIBLE) {
            etInput.requestFocus();
        }
    }

}
