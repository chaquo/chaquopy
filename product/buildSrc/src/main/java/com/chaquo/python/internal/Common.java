package com.chaquo.python.internal;

import java.io.*;
import java.util.*;


/** Constants and utilities shared between the Gradle plugin, the runtime, and their
 * respective build scripts. */
public class Common {
    // Minimum Android Gradle plugin version
    public static final String MIN_AGP_VERSION = "7.0.0";

    // This should match api_level in target/build-common.sh.
    public static final int MIN_SDK_VERSION = 21;

    public static final int COMPILE_SDK_VERSION = 30;

    public static final Map<String, String> PYTHON_VERSIONS = new LinkedHashMap<>();
    static {
        // Version, build number
        PYTHON_VERSIONS.put("3.8.16", "0");
        PYTHON_VERSIONS.put("3.9.13", "1");
        PYTHON_VERSIONS.put("3.10.6", "1");
        PYTHON_VERSIONS.put("3.11.0", "2");
    }

    public static List<String> PYTHON_VERSIONS_SHORT = new ArrayList<>();
    static {
        for (String fullVersion : PYTHON_VERSIONS.keySet()) {
            PYTHON_VERSIONS_SHORT.add(
                fullVersion.substring(0, fullVersion.lastIndexOf('.')));
        }
    }

    // This is the version with the best set of native packages in the repository.
    public static final String DEFAULT_PYTHON_VERSION = "3.8";

    // Wheel tags (PEP 425).
    public static final String PYTHON_IMPLEMENTATION = "cp";  // CPython

    public static final List<String> ABIS = Arrays.asList
        ("armeabi-v7a", "arm64-v8a", "x86", "x86_64");

    // Subdirectory name to use within assets, getFilesDir() and getCacheDir()
    public static final String ASSET_DIR = "chaquopy";

    public static String assetZip(String type) {
        return assetZip(type, null);
    }

    public static String assetZip(String type, String abi) {
        // We need to prevent our ZIP files from being compressed within the APK. This wouldn't
        // save much space (because the files within the ZIP are already compressed), but it
        // would seriously harm performance of AssetFinder, because it would have to read and
        // decompress all the intermediate data every time it seeks within the ZIP (see
        // measurements in #5658).
        //
        // Unfortunately .zip is not one of the default noCompress extensions
        // (frameworks/base/tools/aapt2/cmd/Link.cpp). We used to monkey-patch the noCompress
        // method, but that doesn't carry over from an AAR to the final APK. So we'll just have
        // to rename the AssetFinder ZIPs to one of the extensions in the default list. We use
        // something obscure so that Chaquopy developers can configure their file explorer to
        // treat it as a ZIP without causing any inconvenience.
        String ext = ".imy";
        if (abi == null) {
            return type + ext;
        } else {
            return type + "-" + abi + ext;
        }
    }

    // Parameters for assetZip
    public static final String ABI_COMMON = "common";
    public static final String ASSET_BOOTSTRAP = "bootstrap";
    public static final String ASSET_APP = "app";
    public static final String ASSET_REQUIREMENTS = "requirements";
    public static final String ASSET_STDLIB = "stdlib";

    // Other assets
    public static final String ASSET_BOOTSTRAP_NATIVE = "bootstrap-native";
    public static final String ASSET_BUILD_JSON = "build.json";
    public static final String ASSET_CACERT = "cacert.pem";

    // The default PATH on Mac is /usr/bin:/bin:/usr/sbin:/sbin. However, apps can't
    // install anything into these locations, so the python.org installers use
    // /usr/local/bin instead. This directory may also appear to be on the default PATH,
    // but this is because it's listed in /etc/paths, which only affects shells, not
    // other apps like Android Studio, or its Gradle subprocesses.
    public static String findOnPath(String basename) throws FileNotFoundException {
        List<String> path = new ArrayList<>();
        Collections.addAll(path, System.getenv("PATH").split(File.pathSeparator));
        if (System.getProperty("os.name").toLowerCase().startsWith("mac")) {
            path.add("/usr/local/bin");
        }

        for (String dir : path) {
            File file = new File(dir, basename);
            if (file.exists()) {
                return file.toString();
            }
        }
        throw new FileNotFoundException("Couldn't find '" + basename + "' on PATH");
    }

}
