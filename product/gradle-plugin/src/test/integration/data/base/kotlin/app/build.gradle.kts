plugins {
    id("com.android.application")
    id("com.chaquo.python")
}

android {
    namespace = "com.chaquo.python.test"
    compileSdk = 31

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
