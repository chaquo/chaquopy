package com.chaquo.python;

import java.util.*;


/** @deprecated internal use */
public class Common {
    // API level 15 currently has over 99% support on the Google dashboard, and is the default
    // minimum version for new apps in Android Studio 3.0.
    //
    // Our ability to test older versions is currently limited by the demo app, which uses
    // com.android.support:preference-v14. We could probably support API level 14 as well, but it's
    // too awkward to test because it doesn't have an x86 emulator image.
    public static final int MIN_SDK_VERSION = 15;

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
    public static final String ASSET_APP = "app.zip";
    public static final String ASSET_CHAQUOPY = "chaquopy.zip";
    public static final String ASSET_REQUIREMENTS = "requirements";
    public static final String ASSET_STDLIB = "stdlib.zip";
    public static final String ASSET_TICKET = "ticket.txt";
}