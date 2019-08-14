package com.chaquo.python.android;

import android.app.*;
import android.content.*;
import android.content.res.*;
import android.os.*;
import com.chaquo.python.*;
import java.io.*;
import java.util.*;
import org.json.*;


/** Platform for Chaquopy on Android. */
@SuppressWarnings("deprecation")
public class AndroidPlatform extends Python.Platform {

    // Used in importer.py and test_android.py.
    public static String ABI;

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

        // Renamed to stdlib-common.zip in 6.2.2.
        "stdlib.zip",
    };

    private static final String[] OBSOLETE_CACHE = {
        // Renamed back to .zip in 1.1.0.
        "AssetFinder/app.mp3",
        "AssetFinder/requirements.mp3",

        // Split into requirements-common.zip and requirements-<abi>.zip in 2.1.0.
        "AssetFinder/requirements.zip",

        // Renamed to stdlib-<abi>.zip in 6.2.2.
        "AssetFinder/<abi>.zip",
    };

    /** @deprecated Internal use in chaquopy_java.pyx. */
    public Application mContext;
    private SharedPreferences sp;
    private JSONObject buildJson;
    private AssetManager am;

    /** Uses the {@link android.app.Application} context of the given context to initialize
     * Python. */
    public AndroidPlatform(Context context) {
        mContext = (Application) context.getApplicationContext();
        sp = mContext.getSharedPreferences(Common.ASSET_DIR, Context.MODE_PRIVATE);
        am = mContext.getAssets();

        List<String> supportedAbis = new ArrayList<>();  // In order of preference.
        if (Build.VERSION.SDK_INT >= 21) {
            Collections.addAll(supportedAbis, Build.SUPPORTED_ABIS);
        } else {
            Collections.addAll(supportedAbis, Build.CPU_ABI, Build.CPU_ABI2);
        }

        for (String abi : supportedAbis) {
            try {
                am.open(Common.ASSET_DIR + "/" + Common.assetZip(Common.ASSET_STDLIB, abi));
                ABI = abi;
                break;
            } catch (IOException ignored) {}
        }
        if (ABI == null) {
            throw new RuntimeException("None of this device's ABIs " + supportedAbis +
                                       " are supported by this app.");
        }
    }

    /** Returns the Application context of the context which was passed to the contructor. */
    public Application getApplication() {
        return mContext;
    }

    @Override
    public String getPath() {
        // These assets will be extracted to separate files and used as the initial PYTHONPATH.
        String path = "";
        String assetDir = mContext.getFilesDir() + "/" + Common.ASSET_DIR;
        List<String> bootstrapAssets = new ArrayList<>(Arrays.asList(
            Common.assetZip(Common.ASSET_STDLIB, Common.ABI_COMMON),
            Common.assetZip(Common.ASSET_BOOTSTRAP),
            Common.ASSET_BOOTSTRAP_NATIVE + "/" + ABI));
        for (int i = 0; i < bootstrapAssets.size(); i++) {
            path += assetDir + "/" + bootstrapAssets.get(i);
            if (i < bootstrapAssets.size() - 1) {
                path += ":";
            }
        }

        // Now add some non-Python assets which also need to be pre-extracted.
        Collections.addAll(bootstrapAssets, Common.ASSET_CACERT, Common.ASSET_TICKET);

        try {
            deleteObsolete(mContext.getFilesDir(), OBSOLETE_FILES);
            deleteObsolete(mContext.getCacheDir(), OBSOLETE_CACHE);
            extractAssets(bootstrapAssets);
            loadNativeLibs();
        } catch (IOException | JSONException e) {
            throw new RuntimeException(e);
        }
        return path;
    }

    private void deleteObsolete(File baseDir, String[] filenames) {
        for (String filename : filenames) {
            filename = filename.replace("<abi>", ABI);
            deleteRecursive(new File(baseDir, Common.ASSET_DIR + "/" + filename));
        }
    }

    @Override
    public void onStart(Python py) {
        // These assets will be added to the start of sys.path using AssetFinder paths,
        // so their content will be extracted on demand.
        String[] appPath = {
            Common.ASSET_APP,
            Common.ASSET_REQUIREMENTS,
            Common.ASSET_STDLIB + "-" + ABI,
        };
        py.getModule("java.android").callAttr("initialize", mContext, buildJson, appPath);
    }

    private void extractAssets(List<String> assets) throws IOException, JSONException {
        String buildJsonPath = Common.ASSET_DIR + "/" + Common.ASSET_BUILD_JSON;
        buildJson = new JSONObject(streamToString(am.open(buildJsonPath)));
        JSONObject assetsJson = buildJson.getJSONObject("assets");

        // AssetManager.list() is extremely slow (20 ms per call on the API 23 emulator), so
        // we'll avoid using it.
        Set<String> unextracted = new HashSet<>(assets);
        SharedPreferences.Editor spe = sp.edit();
        for (Iterator i = assetsJson.keys(); i.hasNext(); /**/) {
            String path = (String) i.next();
            for (String ea : assets) {
                if (path.equals(ea) || path.startsWith(ea + "/")) {
                    extractAsset(assetsJson, spe, path);
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

    private void extractAsset(JSONObject assetsJson, SharedPreferences.Editor spe,
                              String path) throws IOException, JSONException {
        String fullPath = Common.ASSET_DIR  + "/" + path;
        File outFile = new File(mContext.getFilesDir(), fullPath);

        // See also similar code in importer.py.
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

        InputStream inStream = am.open(fullPath);
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
