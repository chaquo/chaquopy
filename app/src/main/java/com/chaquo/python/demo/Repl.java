package com.chaquo.python.demo;

import android.support.annotation.*;

import com.google.common.io.*;

import java.io.*;

import static com.chaquo.python.demo.App.context;

public class Repl {
    private static final String STDLIB_FILENAME = "stdlib.zip";

    private static Repl sInstance;

    static {
        // Libraries must be loaded in reverse dependency order before API level 18, see
        // https://developer.android.com/ndk/guides/cpp-support.html
        System.loadLibrary("crystax");
        System.loadLibrary("python2.7");
        System.loadLibrary("repl");
    }

    public static Repl getInstance() {
        if (sInstance == null) {
            ensureStdlib();
            sInstance = new Repl();
        }
        return sInstance;
    }

    private static void ensureStdlib() {
        try {
            File stdlibFile = getStdlibFile();
            if (!stdlibFile.exists()) {
                InputStream stdlibIn = App.context.getAssets().open(STDLIB_FILENAME);
                try {
                    OutputStream stdlibOut = new FileOutputStream(stdlibFile);
                    try {
                        ByteStreams.copy(stdlibIn, stdlibOut);
                    } finally {
                        stdlibOut.close();
                    }
                } finally {
                    stdlibIn.close();
                }
            }
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

    @NonNull
    private static File getStdlibFile() {
        return new File(context.getFilesDir(), STDLIB_FILENAME);
    }


    private long nativeState;

    private Repl() {}

    public void start() {
        nativeStart(getStdlibFile().getAbsolutePath());
    }
    public native void nativeStart(String path);

    public void stop() {
        nativeStop();
    }
    public native void nativeStop();

    public native String eval(String expr);

}
