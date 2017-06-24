package com.chaquo.python.demo;

import android.os.*;

public abstract class UnitTestActivity extends ConsoleActivity {

    private boolean alreadyRun;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        setContentView(R.layout.activity_unit_test);
        super.onCreate(savedInstanceState);
        alreadyRun = (savedInstanceState != null);
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (! alreadyRun) {
            alreadyRun = true;
            new Thread(new Runnable() {
                @Override
                public void run() {
                    runTests();
                }
            }).start();
        }
    }

    protected abstract void runTests();

}
