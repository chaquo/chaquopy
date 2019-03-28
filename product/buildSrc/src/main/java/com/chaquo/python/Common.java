package com.chaquo.python;

import java.util.*;


/** @deprecated internal use */
public class Common {
    // We currently aim for 99% support, based on the numbers at
    // https://developer.android.com/about/dashboards/.
    public static final int MIN_SDK_VERSION = 16;

    // For Build.SUPPORTED_ABIS.
    public static final int COMPILE_SDK_VERSION = 21;

    public static final String PYTHON_VERSION = "3.6.5";
    public static final String PYTHON_VERSION_SHORT =
        PYTHON_VERSION.substring(0, PYTHON_VERSION.lastIndexOf('.'));
    public static final String PYTHON_BUILD_NUM = "10";

    // Library name suffix: may contain flags from PEP 3149.
    public static final String PYTHON_SUFFIX = PYTHON_VERSION_SHORT + "m";

    // Wheel tags (PEP 425).
    public static final String PYTHON_IMPLEMENTATION = "cp";  // CPython
    public static final String PYTHON_ABI =
        PYTHON_IMPLEMENTATION + PYTHON_SUFFIX.replace(".", "");

    public static final List<String> ABIS = Arrays.asList
        ("armeabi-v7a", "arm64-v8a", "x86", "x86_64");

    // Subdirectory name to use within assets, getFilesDir() and getCacheDir()
    public static final String ASSET_DIR = "chaquopy";

    public static final String ASSET_APP = "app.zip";
    public static final String ASSET_BOOTSTRAP = "bootstrap.zip";
    public static final String ASSET_BOOTSTRAP_NATIVE = "bootstrap-native";
    public static String ASSET_REQUIREMENTS(String suffix) {
        return "requirements-" + suffix + ".zip";
    }
    public static final String ASSET_STDLIB = "stdlib.zip";
    public static final String ASSET_STDLIB_NATIVE = "stdlib-native";

    public static final String ASSET_BUILD_JSON = "build.json";
    public static final String ASSET_CACERT = "cacert.pem";
    public static final String ASSET_TICKET = "ticket.txt";

    public static final String ABI_COMMON = "common";
}
