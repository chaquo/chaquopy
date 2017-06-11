package com.chaquo.python;

import java.util.*;


public class Common {
    // This is currently the oldest version included in the NDK. To build the runtime module, the
    // corresponding platform JAR must have been downloaded using the SDK Manager.
    public static final int MIN_SDK_VERSION = 9;

    // TODO #5148 add Python 3
    // TODO #5213 update Python 2.7
    public static final List<String> PYTHON_VERSIONS = Arrays.asList
        ("2.7.10");

    public static String pyVersionNoDot(String version) {
        return version.substring(0, version.lastIndexOf('.')).replace(".", "");
    }

    // This is trivial for Python 2, but for Python 3 it may contain flags from PEP 3149.
    public static final Map<String,String> PYTHON_ABIS = new HashMap<>();
    static {
        PYTHON_ABIS.put("2.7.10", "cp27");
    }

    public static final List<String> ABIS = Arrays.asList
        ("armeabi-v7a",
         "x86"
         // TODO #5198 "armeabi",
         // TODO #5199 "arm64-v8a", "x86_64"
        );

    public static final String ASSET_DIR = "chaquopy";
}