package com.chaquo.python.demo;

public class ReplActivity extends PythonConsoleActivity {

    @Override public void run() {
        input("from java import *\n");
        py.getModule("chaquopy.demo.repl")
            .callAttr("AndroidConsole", this)
            .callAttr("interact");
    }

    @Override public void onBackPressed() {
        if (state.thread.isAlive()) {
            moveTaskToBack(true);
        } else {
            super.onBackPressed();
        }
    }

}
