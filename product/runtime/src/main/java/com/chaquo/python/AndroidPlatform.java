package com.chaquo.python;

import android.content.*;
import android.content.res.*;
import android.os.*;

import java.io.*;


/** Platform for Chaquopy on Android. */
@SuppressWarnings("deprecation")
public class AndroidPlatform implements Python.Platform {
    // Earlier elements take priority over later ones.
    private static final String[] PYTHON_PATH = {
        Common.ASSET_CHAQUOPY,  // Prevent rsa module from being overridden
        Common.ASSET_APP,
        Common.ASSET_REQUIREMENTS,
        Common.ASSET_STDLIB,
        "lib-dynload/" + Build.CPU_ABI,
    };

    /** @deprecated Internal use in chaquopy_java.pyx. */
    public Context mContext;

    /** The context is used only for initialization, and does not need to remain valid after
     * {@link Python#start Python.start()} is called. */
    // TODO #5201 Remove reference once no longer required
    public AndroidPlatform(Context context) {
        mContext = context.getApplicationContext();
        extractAssets();
        loadNativeLibs();
    }

    @Override
    public String getPath() {
        String path = "";
        for (int i = 0; i < PYTHON_PATH.length; i++) {
            path += mContext.getFilesDir() + "/" + Common.ASSET_DIR + "/" + PYTHON_PATH[i];
            if (i < PYTHON_PATH.length - 1) {
                path += ":";
            }
        }
        return path;
    }

    private void extractAssets() {
        // TODO #5158 avoid extraction
        try {
            AssetManager assets = mContext.getAssets();
            for (String path : PYTHON_PATH) {
                extractAssets(assets, Common.ASSET_DIR + "/" + path);
            }

            // No ticket is represented as an empty file rather than a missing one. This saves us
            // from having to delete the extracted copy if the app is updated to remove the ticket.
            // (We could pass the ticket to the runtime in some other way, but that would be more
            // complicated.)
            extractAssets(assets, Common.ASSET_DIR + "/" + Common.ASSET_TICKET);
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

            // TODO #5159 only extract if the asset has changed
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
