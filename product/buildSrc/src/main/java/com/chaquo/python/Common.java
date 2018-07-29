package com.chaquo.python;

import java.util.*;


/** @deprecated internal use */
public class Common {
    // API level 15 currently has over 99% support on the Google dashboard.
    // Our ability to test older versions is currently limited by the demo app,
    // which uses com.android.support:preference-v14. We could probably support
    // API level 14 as well, but it's too awkward to test because it doesn't have
    // an x86 emulator image.
    public static final int MIN_SDK_VERSION = 15;
    public static final int COMPILE_SDK_VERSION = 21;  // For Build.SUPPORTED_ABIS

    public static final List<String> PYTHON_VERSIONS = Arrays.asList
        ("2.7.10", "2.7.14", "2.7.15", "3.6.3", "3.6.5");

    public static final List<String> CURRENT_PYTHON_VERSIONS = Arrays.asList
        ("2.7.15", "3.6.5");

    public static String pyVersionShort(String version) {
        return version.substring(0, version.lastIndexOf('.'));
    }

    // See target/package-target.sh
    public static final Map<String,String> PYTHON_BUILD_NUMBERS = new HashMap<>();
    static {
        PYTHON_BUILD_NUMBERS.put("2.7.10", "2");
        PYTHON_BUILD_NUMBERS.put("2.7.14", "2");
        PYTHON_BUILD_NUMBERS.put("2.7.15", "4");
        PYTHON_BUILD_NUMBERS.put("3.6.3", "3");
        PYTHON_BUILD_NUMBERS.put("3.6.5", "5");
    }

    // This is trivial for Python 2, but for Python 3 it may contain flags from PEP 3149.
    public static final Map<String,String> PYTHON_SUFFIXES = new HashMap<>();
    static {
        PYTHON_SUFFIXES.put("2.7", "2.7");
        PYTHON_SUFFIXES.put("3.6", "3.6m");
    }

    public static final Map<String,String> PYTHON_ABIS = new HashMap<>();
    static {
        for (Map.Entry<String,String> entry : PYTHON_SUFFIXES.entrySet()) {
            PYTHON_ABIS.put(entry.getKey(),
                            "cp" + entry.getValue().replace(".", ""));
        }
    }

    public static final List<String> ABIS = Arrays.asList
        ("armeabi-v7a",
         "x86"
         // TODO #5199 "arm64-v8a", "x86_64"
        );

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