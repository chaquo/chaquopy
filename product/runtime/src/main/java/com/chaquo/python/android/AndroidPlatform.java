package com.chaquo.python.android;

import android.content.*;
import android.content.res.*;
import android.os.*;
import com.chaquo.python.*;
import java.io.*;
import org.json.*;


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

    private static final String[] OBSOLETE_FILES = {
        // No longer extracted since 0.6.0
        "app.zip",
        "requirements.zip",

        // Renamed back to .zip in 0.7.0
        "chaquopy.mp3",
        "stdlib.mp3",
    };

    /** @deprecated Internal use in chaquopy_java.pyx. */
    public Context mContext;

    /** The given context must be an {@link android.app.Activity}, {@link android.app.Service} or
     * {@link android.app.Application} object from your app. The context is used only for
     * initialization, and does not need to remain valid after {@link Python#start Python.start()}
     * is called. */
    // TODO #5201 Remove reference once no longer required
    public AndroidPlatform(Context context) {
        try {
            mContext = context.getApplicationContext();
            for (String filename : OBSOLETE_FILES) {
                new File(mContext.getFilesDir(), Common.ASSET_DIR + "/" + filename).delete();
            }
            JSONObject buildJson = extractAssets();
            loadNativeLibs(buildJson.getString("version"));
        } catch (IOException | JSONException e) {
            throw new RuntimeException(e);
        }
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

    private JSONObject extractAssets() throws IOException, JSONException {
        // TODO #5258 avoid extraction
        AssetManager assets = mContext.getAssets();
        InputStream buildJsonStream = assets.open(Common.ASSET_DIR + "/" + Common.ASSET_BUILD_JSON);
        JSONObject buildJson = new JSONObject(streamToString(buildJsonStream));

        for (String path : BOOTSTRAP_PATH) {
            extractAssets(assets, Common.ASSET_DIR + "/" + path);
        }

        // No ticket is represented as an empty file rather than a missing one. This saves us
        // from having to delete the extracted copy if the app is updated to remove the ticket.
        // (We could pass the ticket to the runtime in some other way, but that would be more
        // complicated.)
        extractAssets(assets, Common.ASSET_DIR + "/" + Common.ASSET_TICKET);

        return buildJson;
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
        deleteRecursive(outFile);
        if (isDir) {
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

    /** This converts all newlines to "\n", and adds a newline at the end of the stream even if
     * none was present, but neither of those things should matter for a text file. */
    private String streamToString(InputStream in) throws IOException {
        BufferedReader reader = new BufferedReader(new InputStreamReader(in));
        StringBuilder out = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            out.append(line);
            out.append("\n");
        }
        return out.toString();
    }

    private void loadNativeLibs(String pyVersion) {
        // Libraries must be loaded in reverse dependency order before API level 18: see
        // https://developer.android.com/ndk/guides/cpp-support.html
        System.loadLibrary("crystax");
        System.loadLibrary("python" + Common.PYTHON_SUFFIXES.get(pyVersion));
        System.loadLibrary("chaquopy_java");
    }

}
