package com.chaquo.python;

import android.content.*;
import android.content.res.*;
import android.os.*;

import java.io.*;


/** Platform for Chaquopy on Android. */
public class AndroidPlatform implements Python.Platform {
    private static final String[] ASSETS = {
        "stdlib.zip",
        "chaquopy.zip",
        "lib-dynload/" + Build.CPU_ABI,
    };

    private Context mContext;

    public AndroidPlatform(Context context) {
        mContext = context;
        extractAssets();
        loadNativeLibs();
    }

    @Override
    public String getPath() {
        String path = "";
        for (int i = 0; i < ASSETS.length; i++) {
            path += mContext.getFilesDir() + "/" + Common.ASSET_DIR + "/" + ASSETS[i];
            if (i < ASSETS.length - 1) {
                path += ":";
            }
        }
        return path;
    }

    @Override
    public boolean shouldInitialize() {
        return true;
    }

    private void extractAssets() {
        // TODO avoid extraction (#5158)
        try {
            for (String path : ASSETS) {
                extractAssets(mContext.getAssets(), Common.ASSET_DIR + "/" + path);
            }
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

    private void extractAssets(AssetManager assets, String path) throws IOException {
        // The documentation doesn't say what list() does if the path isn't a directory, so be
        // cautious.
        boolean isDir;
        try {
            isDir = (assets.list(path).length > 0);
        } catch (IOException e) {
            isDir = false;
        }

        if (isDir) {
            for (String filename : assets.list(path)) {
                extractAssets(assets, path + "/" + filename);
            }
        } else {
            File outDir = new File(mContext.getFilesDir(), new File(path).getParent());
            if (! outDir.exists()) {
                outDir.mkdirs();
                if (! outDir.isDirectory()) {
                    throw new IOException("Failed to create " + outDir);
                }
            }

            // TODO only extract if the asset has changed. Reading flash storage is faster than
            // writing (especially if the file's already in the OS cache), so we could read
            // inStream into a buffer and then compare it with the content of outFile before
            // overwriting it. Or maybe make the Gradle plugin embed a timestamp so we can avoid
            // this entirely.
            InputStream inStream = assets.open(path);
            File outFile = new File(mContext.getFilesDir(), path);
            File tmpFile = new File(outFile.getParent(), outFile.getName() + ".tmp");
            tmpFile.delete();
            OutputStream outStream = new FileOutputStream(tmpFile);
            try {
                transferStream(inStream, outStream);
            } finally {
                outStream.close();
            }
            outFile.delete();
            if (!tmpFile.renameTo(outFile)) {
                throw new IOException("Failed to create " + outFile);
            }
        }
    }

    private void transferStream(InputStream in, OutputStream out) throws IOException {
        byte[] buffer = new byte[1024 * 1024];
        int len = in.read(buffer);
        while (len != -1) {
            out.write(buffer, 0, len);
            len = in.read(buffer);
        }
    }

    private void loadNativeLibs() {
        // Libraries must be loaded in reverse dependency order before API level 18: see
        // https://developer.android.com/ndk/guides/cpp-support.html
        System.loadLibrary("crystax");
        System.loadLibrary("python2.7");  // TODO #5148
        System.loadLibrary("chaquopy_java");
    }

}
