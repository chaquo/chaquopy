package com.chaquo.python.android;

import android.content.*;
import android.content.res.*;
import android.os.*;
import android.util.*;
import com.chaquo.python.*;
import java.io.*;
import java.util.*;
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

        // Renamed back to .zip in 1.1.0
        "chaquopy.mp3",
        "stdlib.mp3",
    };

    private static final String[] OBSOLETE_CACHE = {
        // Renamed back to .zip in 1.1.0
        "AssetFinder/app.mp3",
        "AssetFinder/requirements.mp3",
    };

    /** @deprecated Internal use in chaquopy_java.pyx. */
    public Context mContext;
    private SharedPreferences sp;

    /** The given context must be an {@link android.app.Activity}, {@link android.app.Service} or
     * {@link android.app.Application} object from your app. The context is used only for
     * initialization, and does not need to remain valid after {@link Python#start Python.start()}
     * is called. */
    // TODO #5201 Remove reference once no longer required
    public AndroidPlatform(Context context) {
        mContext = context.getApplicationContext();
        sp = mContext.getSharedPreferences(Common.ASSET_DIR, Context.MODE_PRIVATE);
    }

    @Override
    public String getPath() {
        try {
            deleteObsolete(mContext.getFilesDir(), OBSOLETE_FILES);
            deleteObsolete(mContext.getCacheDir(), OBSOLETE_CACHE);

            JSONObject buildJson = extractAssets();
            loadNativeLibs(Common.pyVersionShort(buildJson.getString("version")));
        } catch (IOException | JSONException e) {
            throw new RuntimeException(e);
        }

        String path = "";
        for (int i = 0; i < BOOTSTRAP_PATH.length; i++) {
            path += mContext.getFilesDir() + "/" + Common.ASSET_DIR + "/" + BOOTSTRAP_PATH[i];
            if (i < BOOTSTRAP_PATH.length - 1) {
                path += ":";
            }
        }
        return path;
    }

    private void deleteObsolete(File baseDir, String[] filenames) {
        for (String filename : filenames) {
            deleteRecursive(new File(baseDir, Common.ASSET_DIR + "/" + filename));
        }
    }

    @Override
    public void onStart(Python py) {
        py.getModule("java.android").callAttr("initialize", mContext, APP_PATH);
    }

    private JSONObject extractAssets() throws IOException, JSONException {
        AssetManager assets = mContext.getAssets();
        String buildJsonPath = Common.ASSET_DIR + "/" + Common.ASSET_BUILD_JSON;
        JSONObject buildJson = new JSONObject(streamToString(assets.open(buildJsonPath)));
        JSONObject assetsJson = buildJson.getJSONObject("assets");
        SharedPreferences.Editor spe = sp.edit();

        // AssetManager.list() is extremely slow (20 ms per call on the API 23 emulator), so we'll
        // avoid using it.
        for (Iterator i = assetsJson.keys(); i.hasNext(); /**/) {
            String path = (String) i.next();
            for (String bsp : BOOTSTRAP_PATH) {
                if (path.equals(bsp) || path.startsWith(bsp + "/")) {
                    extractAsset(assets, assetsJson, spe, path);
                    break;
                }
            }
        }

        // No ticket is represented as an empty file rather than a missing one. This saves us
        // from having to delete the extracted copy if the app is updated to remove the ticket.
        // (We could pass the ticket to the runtime in some other way, but that would be more
        // complicated.)
        extractAsset(assets, assetsJson, spe, Common.ASSET_TICKET);

        spe.apply();
        return buildJson;
    }

    private void extractAsset(AssetManager assets, JSONObject assetsJson, SharedPreferences.Editor spe,
                              String path) throws IOException, JSONException {
        String fullPath = Common.ASSET_DIR  + "/" + path;
        File outFile = new File(mContext.getFilesDir(), fullPath);
        String spKey = "asset." + path;
        String newHash = assetsJson.getString(path);
        if (outFile.exists() && sp.getString(spKey, "").equals(newHash)) {
            return;
        }

        outFile.delete();
        File outDir = outFile.getParentFile();
        if (!outDir.exists()) {
            outDir.mkdirs();
            if (!outDir.isDirectory()) {
                throw new IOException("Failed to create " + outDir);
            }
        }

        InputStream inStream = assets.open(fullPath);
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
        spe.putString(spKey, newHash);
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

    private void loadNativeLibs(String pyVersionShort) {
        // Libraries must be loaded in reverse dependency order before API level 18: see
        // https://developer.android.com/ndk/guides/cpp-support.html
        System.loadLibrary("crystax");
        System.loadLibrary("python" + Common.PYTHON_SUFFIXES.get(pyVersionShort));
        System.loadLibrary("chaquopy_java");
    }

}
