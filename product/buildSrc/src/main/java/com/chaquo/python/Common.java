package com.chaquo.python;


import java.util.*;

public class Common {
    public static final List<String> PYTHON_VERSIONS = Arrays.asList
        ("2.7.10");                                                     // TODO #5148
    public static final List<String> ABIS = Arrays.asList
        ("armeabi-v7a",
         "x86"
         // TODO #5198 "armeabi",
         // TODO #5199 "arm64-v8a", "x86_64"
        );
    public static final String ASSET_DIR = "chaquopy";
}