package com.chaquo.python;

import java.util.*;


/** @deprecated internal use */
public class Common {
    public static final int MIN_SDK_VERSION = 16;

    // For Build.SUPPORTED_ABIS.
    public static final int COMPILE_SDK_VERSION = 21;

    public static final String PYTHON_VERSION = "3.8.1";
    public static final String PYTHON_VERSION_SHORT =
        PYTHON_VERSION.substring(0, PYTHON_VERSION.lastIndexOf('.'));
    public static final String PYTHON_VERSION_MAJOR =
        PYTHON_VERSION.substring(0, PYTHON_VERSION.indexOf('.'));
    public static final String PYTHON_BUILD_NUM = "1";

    // Library name suffix: may contain flags from PEP 3149.
    public static final String PYTHON_SUFFIX = PYTHON_VERSION_SHORT;

    // Wheel tags (PEP 425).
    public static final String PYTHON_IMPLEMENTATION = "cp";  // CPython
    public static final String PYTHON_ABI =
        PYTHON_IMPLEMENTATION + PYTHON_SUFFIX.replace(".", "");

    public static final List<String> ABIS = Arrays.asList
        ("armeabi-v7a", "arm64-v8a", "x86", "x86_64");

    // Subdirectory name to use within assets, getFilesDir() and getCacheDir()
    public static final String ASSET_DIR = "chaquopy";

    public static String assetZip(String type) { return assetZip(type, null); }
    public static String assetZip(String type, String abi) {
        if (abi == null) {
            return type + ".zip";
        } else {
            return type + "-" + abi + ".zip";
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
    public static final String ASSET_TICKET = "ticket.txt";
}
