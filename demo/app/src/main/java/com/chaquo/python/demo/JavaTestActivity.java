package com.chaquo.python.demo;

import android.os.*;
import android.support.v7.app.*;
import android.text.*;
import android.view.*;
import android.widget.*;

import junit.runner.*;

import org.junit.runner.*;
import org.junit.runner.notification.*;

public class JavaTestActivity extends AppCompatActivity {
    private ScrollView svBuffer;
    private TextView tvBuffer;
    private boolean alreadyRun = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_unit_test);
        svBuffer = (ScrollView) findViewById(R.id.svBuffer);
        tvBuffer = (TextView) findViewById(R.id.tvBuffer);
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (! alreadyRun) {
            new Thread(new Runnable() {
                @Override
                public void run() {
                    JUnitCore juc = new JUnitCore();
                    juc.addListener(new Listener());
                    juc.run(JavaTestSuite.class);
                    alreadyRun = true;
                }
            }).start();
        }
    }

    private class Listener extends RunListener {
        @Override
        public void testStarted(Description description) throws Exception {
            append(description.toString(), true);
        }

        @Override
        public void testIgnored(Description description) throws Exception {
            append("IGNORED");
        }

        @Override
        public void testFailure(Failure failure) throws Exception {
            append(BaseTestRunner.getFilteredTrace(failure.getException()));
        }

        @Override
        public void testAssumptionFailure(Failure failure) {
            append("ASSUMPTION FAILED");
        }

        @Override
        public void testRunFinished(Result result) throws Exception {
            append(String.format("Ran %s tests in %.3f seconds (%s failed, %s ignored)",
                                 result.getRunCount(), result.getRunTime() / 1000.0,
                                 result.getFailureCount(), result.getIgnoreCount()),
                   true);
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
                svBuffer.fullScroll(View.FOCUS_UP);
            } break;

            case R.id.menu_bottom: {
                svBuffer.fullScroll(View.FOCUS_DOWN);
            } break;

            default: return false;
        }
        return true;
    }

    private void append(String text) {
        append(text, false);
    }

    private void append(String text, boolean highlight) {
        if (text.endsWith("\n")) {
            text = text.substring(0, text.length() - 1);
        }
        if (text.length() == 0) return;

        final CharSequence appendText;
        if (highlight) {
            appendText = Html.fromHtml("<b>" + text + "</b");
        } else {
            appendText = text;
        }

        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                if (tvBuffer.getText().length() > 0) {
                    tvBuffer.append("\n");
                }
                tvBuffer.append(appendText);
                svBuffer.post(new Runnable() {
                    @Override
                    public void run() {
                        svBuffer.fullScroll(View.FOCUS_DOWN);
                    }
                });
            }
        });
    }

}
