package com.chaquo.python;

import java.util.*;


/** @deprecated internal use */
public class Common {
    public static final int MIN_SDK_VERSION = 16;
    public static final int COMPILE_SDK_VERSION = 30;

    public static final Map<String, String> PYTHON_VERSIONS = new LinkedHashMap<>();
    static {
        // Version, build number
        PYTHON_VERSIONS.put("3.8.13", "1");
        PYTHON_VERSIONS.put("3.9.13", "0");
        PYTHON_VERSIONS.put("3.10.6", "0");
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
}
