plugins {
    id("com.android.application")
    id("com.chaquo.python")
}

android {
    namespace = "com.chaquo.python.test"

    // 35 and higher fail on AGP 8.0 and older with the error:
    //
    // > A failure occurred while executing com.android.build.gradle.internal.res.LinkApplicationAndroidResourcesTask$TaskAction
    //   > Android resource linking failed
    //     aapt2 E 10-05 22:22:44 17468 18974953 LoadedArsc.cpp:94] RES_TABLE_TYPE_TYPE entry offsets overlap actual entry data.
    //     aapt2 E 10-05 22:22:44 17468 18974953 ApkAssets.cpp:149] Failed to load resources table in APK '/Users/msmith/Library/Android/sdk/platforms/android-35/android.jar'.
    //     error: failed to load include path /Users/msmith/Library/Android/sdk/platforms/android-35/android.jar.
    compileSdk = 34

    defaultConfig {
        applicationId = "com.chaquo.python.test"
        minSdk = 24
        targetSdk = 31
        versionCode = 1
        versionName = "0.0.1"
        ndk {
            abiFilters += "x86"
        }
    }
}
