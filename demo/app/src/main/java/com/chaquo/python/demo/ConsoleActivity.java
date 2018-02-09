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
        Thread thread;
        boolean pendingNewline = false;  // Prevent empty line at bottom of screen
        int scrollOffset;                // Character offset within tvOutput

        public State(ConsoleActivity activity) {
            thread = new Thread() {
                @Override
                public void run() {
                    ConsoleActivity.this.run();
                    output("[Finished]",
                           new ForegroundColorSpan(getResources().getColor(R.color.console_meta)));
                    etInput.setText("");
                    etInput.setEnabled(false);
                }
            };

        }
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

    private void onCreateInput() {
        etInput = (EditText) findViewById(R.id.etInput);

        // Strip formatting from pasted text.
        etInput.addTextChangedListener(new TextWatcher() {
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            public void onTextChanged(CharSequence s, int start, int before, int count) {}
            @Override
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
                    String text = etInput.getText().toString() + "\n";
                    etInput.setText("");
                    input(text);
                    return true;
                }
                return false;
            }
        });
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
                //   * Keyboard is shown or hidden.
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
        tvOutput.addTextChangedListener(new RemoveCursorWatcher());
    }

    // Because we've set textIsSelectable, the TextView will create an invisible cursor (i.e. a
    // zero-length selection) during startup, and re-create it if necessary whenever the user taps
    // on the view. When a cursor exists, a focused TextView will adjust its containing ScrollView
    // to keep the cursor on-screen at various times, including whenever the text changes and after
    // a screen rotation. textIsSelectable implies focusable, so if there are no other focusable
    // views in the layout, then it will indeed be focused.
    //
    // This interferes with our own scroll control, so we'll remove the cursor whenever we can.
    // Non-zero-length selections are left untouched.
    private static class RemoveCursorWatcher implements TextWatcher {
        SpanWatcher sw = new SpanWatcher() {
            @Override
            public void onSpanAdded(Spannable text, Object what, int start, int end) {
                removeCursor(text);
            }
            @Override
            public void onSpanChanged(Spannable text, Object what, int ostart, int oend, int nstart,
                                      int nend) {
                removeCursor(text);
            }
            public void onSpanRemoved(Spannable text, Object what, int start, int end) {}
        };

        public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
        public void onTextChanged(CharSequence s, int start, int before, int count) {}
        @Override
        public void afterTextChanged(Editable e) {
            removeCursor(e);
            e.setSpan(sw, 0, e.length(), Spanned.SPAN_INCLUSIVE_INCLUSIVE);
        }

        void removeCursor(Spannable s) {
            int selStart = Selection.getSelectionStart(s);
            int selEnd = Selection.getSelectionEnd(s);
            if (selStart != -1 && selStart == selEnd) {
                Selection.removeSelection(s);
            }
        }
    }

    public void input(String text) {
        output(text, new StyleSpan(Typeface.BOLD));
        onInput(text);
    }

    public void setInputEnabled(boolean enabled) {
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
    protected void onResume() {
        super.onResume();
        if (state.thread.getState() == Thread.State.NEW) {
            tvOutput.setText("");  // We may have restored the output from a previous instance.
            state.thread.start();
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        //saveScroll(); // FIXME unnecessary?
    }

    public void onBackPressed() {
        if (state.thread.isAlive()) {
            moveTaskToBack(true);
        }
    }

    /** Override this method to provide the activity's implementation. It will be called on a
     *  background thread. It can call `output` on any thread to add text to the console output. */
    public abstract void run();

    /** Called each time the user enters a line of input. The default implementation does nothing.
     * If you override this method, you should also call `setInputEnabled(true)`. */
    public void onInput(String input) {}

    public void output(CharSequence text, Object... spans) {
        Spannable spanText = new SpannableStringBuilder(text);
        for (Object span : spans) {
            spanText.setSpan(span, 0, text.length(), 0);
        }
        output(spanText);
    }

    public void output(final CharSequence text) {
        if (text.length() == 0) return; // FIXME remove
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

                if (atBottom) {
                    // Auto-scroll once the TextView has updated its layout.
                    svOutput.post(new Runnable() {
                        @Override
                        public void run() {
                            scroll(View.FOCUS_DOWN);
                        }
                    });
                }
            }
        });
    }

    // After a rotation or a keyboard show/hide, a ScrollView will restore the previous pixel scroll
    // position. However, due to re-wrapping, this may result in a completely different piece of
    // text being visible. We'll try to maintain the text position of the top line, unless the view
    // is scrolled to the bottom, in which case we'll maintain that.
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
        svOutput.scrollTo(0, scrollY);

        //svOutput.smoothScrollTo(0, scrollY); // FIXME explain why smooth, or maybe unnecessary now
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
