package com.chaquo.python.android;

import android.content.*;
import android.content.res.*;
import android.os.*;

import android.util.*;
import com.chaquo.python.*;
import java.io.*;


/** Platform for Chaquopy on Android. */
@SuppressWarnings("deprecation")
public class AndroidPlatform extends Python.Platform {
    
    private static final String[] BOOTSTRAP_PATH = {
        Common.ASSET_CHAQUOPY,
        Common.ASSET_STDLIB,
        "lib-dynload/" + Build.CPU_ABI,
    };

    private static final String[] APP_PATH = {
        Common.ASSET_APP,
        Common.ASSET_REQUIREMENTS,
    };

    /** @deprecated Internal use in chaquopy_java.pyx. */
    public Context mContext;

    /** The given context must be an {@link android.app.Activity}, {@link android.app.Service} or
     * {@link android.app.Application} object from your app. The context is used only for
     * initialization, and does not need to remain valid after {@link Python#start Python.start()}
     * is called. */
    // TODO #5201 Remove reference once no longer required
    public AndroidPlatform(Context context) {
        mContext = context.getApplicationContext();
        extractAssets();
        loadNativeLibs();
    }

    @Override
    public String getPath() {
        String path = "";
        for (int i = 0; i < BOOTSTRAP_PATH.length; i++) {
            path += mContext.getFilesDir() + "/" + Common.ASSET_DIR + "/" + BOOTSTRAP_PATH[i];
            if (i < BOOTSTRAP_PATH.length - 1) {
                path += ":";
            }
        }
        return path;
    }

    @Override
    public void onStart(Python py) {
        py.getModule("java.android.importer").callAttr("initialize", mContext);
        PyObject path = py.getModule("sys").get("path");
        for (int i = 0; i < APP_PATH.length; i++) {
            path.callAttr("insert", i, "/android_asset/" + Common.ASSET_DIR + "/" + APP_PATH[i]);
        }
    }

    private void extractAssets() {
        // TODO #5258 avoid extraction
        try {
            AssetManager assets = mContext.getAssets();
            for (String path : BOOTSTRAP_PATH) {
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

    /** @param path A path which will be read relative to the assets and written relative to
     *      getFilesDir(). If this is a directory, it will be copied recursively, and
     *      any existing directory with that name will be deleted. */
    private void extractAssets(AssetManager assets, String path) throws IOException {
        // The documentation doesn't say what list() does if the path isn't a directory, so be
        // cautious.
        boolean isDir;
        try {
            isDir = (assets.list(path).length > 0);
        } catch (IOException e) {
            isDir = false;
        }

        File outFile = new File(mContext.getFilesDir(), path);
        if (isDir) {
            deleteRecursive(outFile);
            for (String filename : assets.list(path)) {
                extractAssets(assets, path + "/" + filename);
            }
        } else {
            File outDir = outFile.getParentFile();
            if (! outDir.exists()) {
                outDir.mkdirs();
                if (! outDir.isDirectory()) {
                    throw new IOException("Failed to create " + outDir);
                }
            }

            InputStream inStream = assets.open(path);
            File tmpFile = new File(outDir, outFile.getName() + ".tmp");
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

    private void deleteRecursive(File file) {
        File[] children = file.listFiles();
        if (children != null) {
            for (File child : children) {
                deleteRecursive(child);
            }
        }
        file.delete();
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
