package com.chaquo.python.demo;

import com.google.common.io.*;

import java.io.*;

import static com.chaquo.python.demo.App.context;

public class Repl {
    private static final String STDLIB_FILENAME = "stdlib.zip";
    private static final String[] ASSETS = {STDLIB_FILENAME};

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
            extractAssets();
            sInstance = new Repl();
        }
        return sInstance;
    }

    private static void extractAssets() {
        for (String filename : ASSETS) {
            try {
                File outFile = new File(context.getFilesDir(), filename);
                if (!outFile.exists()) {
                    InputStream inStream = App.context.getAssets().open(filename);
                    try {
                        OutputStream outStream = new FileOutputStream(outFile);
                        try {
                            ByteStreams.copy(inStream, outStream);
                        } finally {
                            outStream.close();
                        }
                    } finally {
                        inStream.close();
                    }
                }
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
        }
    }


    private long nativeState;

    private Repl() {}

    public void start() {
        nativeStart(new File(App.context.getFilesDir(), STDLIB_FILENAME).getAbsolutePath());
    }
    public native void nativeStart(String path);

    public void stop() {
        nativeStop();
    }
    public native void nativeStop();

    public native String exec(String line);

}
