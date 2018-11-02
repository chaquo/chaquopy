package com.chaquo.python.android;

import android.app.*;
import android.content.*;
import android.content.res.*;
import android.os.*;
import android.text.*;
import com.chaquo.python.*;
import java.io.*;
import java.util.*;
import org.json.*;


/** Platform for Chaquopy on Android. */
@SuppressWarnings("deprecation")
public class AndroidPlatform extends Python.Platform {

    public static String ABI;  // Can't be final because it's assigned in a loop.
    static {
        String[] SUPPORTED_ABIS;
        if (Build.VERSION.SDK_INT >= 21) {
            SUPPORTED_ABIS = Build.SUPPORTED_ABIS;
        } else {
            SUPPORTED_ABIS = new String[] { Build.CPU_ABI, Build.CPU_ABI2 };
        }
        for (String abi : SUPPORTED_ABIS) {
            if (Common.ABIS.contains(abi)) {
                ABI = abi;
                break;
            }
        }
        if (ABI == null) {
            throw new RuntimeException("Couldn't identify ABI from list [" +
                                       TextUtils.join(", ", SUPPORTED_ABIS) + "]");
        }
    }

    // These assets will be extracted to <data-dir>/files/chaquopy before starting Python.
    private static final List<String> BOOTSTRAP_PATH = new ArrayList<>();
    static {
        BOOTSTRAP_PATH.add(Common.ASSET_STDLIB);
        BOOTSTRAP_PATH.add(Common.ASSET_BOOTSTRAP);
        BOOTSTRAP_PATH.add(Common.ASSET_BOOTSTRAP_NATIVE + "/" + ABI);
    }

    private static final List<String> EXTRACT_ASSETS = new ArrayList<>();
    static {
        EXTRACT_ASSETS.addAll(BOOTSTRAP_PATH);
        EXTRACT_ASSETS.add(Common.ASSET_CACERT);
        EXTRACT_ASSETS.add(Common.ASSET_TICKET);
    }

    // These assets will be extracted on demand using an /android_asset path.
    // The final sys.path will be APP_PATH then BOOTSTRAP_PATH, in that order.
    private static final List<String> APP_PATH = new ArrayList<>();
    static {
        APP_PATH.add(Common.ASSET_APP);
        APP_PATH.add(Common.ASSET_REQUIREMENTS(Common.ABI_COMMON));
        APP_PATH.add(Common.ASSET_REQUIREMENTS(ABI));
        APP_PATH.add(Common.ASSET_STDLIB_NATIVE + "/" + ABI + ".zip");
    }

    private static final String[] OBSOLETE_FILES = {
        // No longer extracted since 0.6.0
        "app.zip",
        "requirements.zip",

        // Renamed back to .zip in 1.1.0
        "chaquopy.mp3",
        "stdlib.mp3",

        // Renamed to bootstrap.zip in 1.3.0
        "chaquopy.zip",

        // Split into bootstrap-native and stdlib-native/<abi>.zip in 1.3.0
        "lib-dynload",
    };

    private static final String[] OBSOLETE_CACHE = {
        // Renamed back to .zip in 1.1.0 (these are directories, not files)
        "AssetFinder/app.mp3",
        "AssetFinder/requirements.mp3",

        // Split into requirements-common.zip and requirements-<abi>.zip in 2.1.0. This is a
        // directory, not a file.
        "AssetFinder/requirements.zip",
    };

    /** @deprecated Internal use in chaquopy_java.pyx. */
    public Application mContext;
    private SharedPreferences sp;
    private JSONObject buildJson;

    /** Uses the {@link android.app.Application} context of the given context to initialize
     * Python. */
    public AndroidPlatform(Context context) {
        mContext = (Application) context.getApplicationContext();
        sp = mContext.getSharedPreferences(Common.ASSET_DIR, Context.MODE_PRIVATE);
    }

    /** Returns the Application context of the context which was passed to the contructor. */
    public Application getApplication() {
        return mContext;
    }

    @Override
    public String getPath() {
        try {
            deleteObsolete(mContext.getFilesDir(), OBSOLETE_FILES);
            deleteObsolete(mContext.getCacheDir(), OBSOLETE_CACHE);
            extractAssets();
            loadNativeLibs();
        } catch (IOException | JSONException e) {
            throw new RuntimeException(e);
        }

        String path = "";
        for (int i = 0; i < BOOTSTRAP_PATH.size(); i++) {
            path += mContext.getFilesDir() + "/" + Common.ASSET_DIR + "/" + BOOTSTRAP_PATH.get(i);
            if (i < BOOTSTRAP_PATH.size() - 1) {
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
        py.getModule("java.android").callAttr(
            "initialize", mContext, buildJson, APP_PATH.toArray());
    }

    private void extractAssets() throws IOException, JSONException {
        AssetManager assets = mContext.getAssets();
        String buildJsonPath = Common.ASSET_DIR + "/" + Common.ASSET_BUILD_JSON;
        buildJson = new JSONObject(streamToString(assets.open(buildJsonPath)));
        JSONObject assetsJson = buildJson.getJSONObject("assets");

        // AssetManager.list() is extremely slow (20 ms per call on the API 23 emulator), so we'll
        // avoid using it.
        Set<String> unextracted = new HashSet<>(EXTRACT_ASSETS);
        SharedPreferences.Editor spe = sp.edit();
        for (Iterator i = assetsJson.keys(); i.hasNext(); /**/) {
            String path = (String) i.next();
            for (String ea : EXTRACT_ASSETS) {
                if (path.equals(ea) || path.startsWith(ea + "/")) {
                    extractAsset(assets, assetsJson, spe, path);
                    unextracted.remove(ea);
                    break;
                }
            }
        }
        if (! unextracted.isEmpty()) {
            throw new RuntimeException("Failed to extract assets: " + unextracted);
        }
        spe.apply();
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

    private void loadNativeLibs() {
        // Libraries must be loaded in dependency order before API level 18 (#5323).
        System.loadLibrary("crystax");

        // build_target_openssl.sh changes the SONAMEs to avoid clashing with the system copies.
        // This isn't necessary for SQLite because the system copy is just "libsqlite.so", with
        // no "3".
        System.loadLibrary("crypto_chaquopy");
        System.loadLibrary("ssl_chaquopy");
        System.loadLibrary("sqlite3");
        System.loadLibrary("python" + Common.PYTHON_SUFFIX);
        System.loadLibrary("chaquopy_java");
    }

}
