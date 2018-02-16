package com.chaquo.python.demo;

import android.graphics.*;
import android.os.*;
import android.support.v4.content.*;
import android.support.v7.app.*;
import android.text.*;
import android.text.style.*;
import android.view.*;
import android.view.inputmethod.*;
import android.widget.*;

public abstract class ConsoleActivity extends AppCompatActivity
implements ViewTreeObserver.OnGlobalLayoutListener {

    private EditText etInput;
    private ScrollView svOutput;
    private TextView tvOutput;
    private int outputWidth = 0, outputHeight = 0;
    private InputListener inputListener;

    enum Scroll {
        TOP, BOTTOM
    }
    private Scroll scrollRequest;
    
    protected static class State {
        Thread thread;
        boolean pendingNewline = false;  // Prevent empty line at bottom of screen
        int scrollChar = 0;              // Character offset of the top visible line.
        int scrollAdjust = 0;            // Pixels by which that line is scrolled above the top
                                         //   (prevents movement when keyboard hidden/shown).
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
        createInput();
        createOutput();
    }

    private void createInput() {
        etInput = findViewById(R.id.etInput);

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
                    String text = etInput.getText().toString() + "\n";
                    etInput.setText("");
                    input(text);
                    return true;
                }
                return false;
            }
        });

    }

    /** Enables input and displays the input box. To disable input, pass null. */
    public void setInputListener(InputListener listener) {
        inputListener = listener;
        runOnUiThread(new Runnable() {
            @Override public void run() {
                if (inputListener != null) {
                    etInput.setVisibility(View.VISIBLE);
                    etInput.requestFocus();
                } else {
                    etInput.setVisibility(View.GONE);
                }
            }
        });
    }

    public InputListener getInputListener() {
        return inputListener;
    }

    public interface InputListener {
        /** Called on the UI thread each time the user enters some input, or input() is called. If
         * the input came from the user, a trailing newline is always included. */
        void onInput(String text);
    }

    /** Generates input as if it had been typed. A trailing newline is *not* automatically added. */
    public void input(final String text) {
        runOnUiThread(new Runnable() {
            @Override public void run() {
                output(span(text, new StyleSpan(Typeface.BOLD)));
                scrollTo(Scroll.BOTTOM);
                inputListener.onInput(text);
            }
        });
    }

    private void createOutput() {
        svOutput = findViewById(R.id.svOutput);
        svOutput.getViewTreeObserver().addOnScrollChangedListener(
            new ViewTreeObserver.OnScrollChangedListener() {
                @Override public void onScrollChanged() { saveScroll(); }
            });

        svOutput.getViewTreeObserver().addOnGlobalLayoutListener(this);

        tvOutput = findViewById(R.id.tvOutput);
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

    @Override protected void onRestoreInstanceState(Bundle savedInstanceState) {
        // Don't restore the UI state unless we have the non-UI state as well.
        if (state.thread != null) {
            super.onRestoreInstanceState(savedInstanceState);
        }
    }

    @Override protected void onResume() {
        super.onResume();
        if (state.thread == null) {
            state.thread = new Thread(getClass().getSimpleName()) {
                @Override public void run() {
                    ConsoleActivity.this.run();
                    output(spanColor("[Finished]", R.color.console_meta));
                    etInput.setEnabled(false);
                    ((InputMethodManager)getSystemService(INPUT_METHOD_SERVICE))
                        .hideSoftInputFromInputMethod(tvOutput.getWindowToken(), 0);
                }
            };
            state.thread.start();
        }
    }

    /** Override this method to provide the activity's implementation. It will be called on a
     *  background thread. */
    public abstract void run();

    // This callback is run after onResume, after each layout pass. If a view's size, position
    // or visibility has changed, the new values will be visible here.
    @Override public void onGlobalLayout() {
        if (outputWidth != svOutput.getWidth() || outputHeight != svOutput.getHeight()) {
            // Either we've just started up, or the keyboard has been hidden or shown.
            outputWidth = svOutput.getWidth();
            outputHeight = svOutput.getHeight();
            restoreScroll();
        } else if (scrollRequest != null) {
            int y = -1;
            switch (scrollRequest) {
                case TOP:
                    y = 0;
                    break;
                case BOTTOM:
                    y = tvOutput.getHeight();
                    break;
            }

            // Don't use smooth scroll, because if an output call happens while it's animating
            // towards the bottom, isScrolledToBottom will believe we've left the bottom and
            // auto-scrolling will stop. Don't use fullScroll either, because not only does it use
            // smooth scroll, it also grabs focus.
            svOutput.scrollTo(0, y);
            scrollRequest = null;
        }
    }

    // After a rotation, a ScrollView will restore the previous pixel scroll position. However, due
    // to re-wrapping, this may result in a completely different piece of text being visible. We'll
    // try to maintain the text position of the top line, unless the view is scrolled to the bottom,
    // in which case we'll maintain that. Maintaining the bottom line will also cause a scroll
    // adjustment when the keyboard's hidden or shown.
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
        removeCursor();
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

    @Override public boolean onOptionsItemSelected(MenuItem item) {
        switch (item.getItemId()) {
            case R.id.menu_top: {
                scrollTo(Scroll.TOP);
            } break;

            case R.id.menu_bottom: {
                scrollTo(Scroll.BOTTOM);
            } break;

            default: return false;
        }
        return true;
    }

    public void outputError(CharSequence text) {
        output(spanColor(text, R.color.console_error));
    }

    public Spannable spanColor(CharSequence text, int colorId) {
        int color = ContextCompat.getColor(this, colorId);
        return span(text, new ForegroundColorSpan(color));
    }

    public static Spannable span(CharSequence text, Object... spans) {
        Spannable spanText = new SpannableStringBuilder(text);
        for (Object span : spans) {
            spanText.setSpan(span, 0, text.length(), 0);
        }
        return spanText;
    }

    public void output(final CharSequence text) {
        if (text.length() == 0) return;
        runOnUiThread(new Runnable() {
            @Override public void run() {
                removeCursor();
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

                // Changes to the TextView height won't be reflected by getHeight until after the
                // next layout pass, so isScrolledToBottom is safe here.
                if (isScrolledToBottom()) {
                    scrollTo(Scroll.BOTTOM);
                }
            }
        });
    }

    // Don't actually scroll until the next onGlobalLayout, when we'll know what the new TextView
    // height is.
    private void scrollTo(Scroll request) {
        // The "top" button should take priority over an auto-scroll.
        if (scrollRequest != Scroll.TOP) {
            scrollRequest = request;
            svOutput.requestLayout();
        }
    }

    // Because we've set textIsSelectable, the TextView will create an invisible cursor (i.e. a
    // zero-length selection) during startup, and re-create it if necessary whenever the user taps
    // on the view. When a TextView is focused and it has a cursor, it will adjust its containing
    // ScrollView whenever the text changes in an attempt to keep the cursor on-screen.
    // textIsSelectable implies focusable, so if there are no other focusable views in the layout,
    // then it will always be focused.
    //
    // To avoid interference from this, we'll remove any cursor before we adjust the scroll.
    // Non-zero-length selections are left untouched.
    private void removeCursor() {
        int selStart = tvOutput.getSelectionStart();
        int selEnd = tvOutput.getSelectionEnd();
        if (selStart != -1 && selStart == selEnd) {
            Selection.removeSelection((Spannable) tvOutput.getText());
        }
    }

}
