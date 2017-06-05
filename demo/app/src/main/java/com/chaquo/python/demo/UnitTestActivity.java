package com.chaquo.python.demo;

import android.os.*;

public abstract class UnitTestActivity extends ConsoleActivity {

    private boolean alreadyRun = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        setContentView(R.layout.activity_unit_test);
        super.onCreate(savedInstanceState);
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (! alreadyRun) {
            new Thread(new Runnable() {
                @Override
                public void run() {
                    runTests();
                    alreadyRun = true;
                }
            }).start();
        }
    }

    protected abstract void runTests();

}
