plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.chaquo.python")
}

afterEvaluate {
    val assetsSrcDir = "src/main/assets/source"
    delete(assetsSrcDir)
    mkdir(assetsSrcDir)
    for (filename in listOf("python/chaquopy/demo/ui_demo.py",
                            "java/com/chaquo/python/demo/JavaDemoActivity.java")) {
        val srcFile = file("src/main/$filename")
        if (! srcFile.exists()) {
            throw GradleException("$srcFile does not exist")
        }
        copy {
            from(srcFile)
            into(assetsSrcDir)
        }
    }
}

android {
    namespace = "com.chaquo.python.demo"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.chaquo.python.demo3"
        minSdk = 21
        targetSdk = 34

        val plugins = buildscript.configurations.getByName("classpath")
             .resolvedConfiguration.resolvedArtifacts.map {
                 it.moduleVersion.id
            }.filter {
                it.group == "com.chaquo.python" && it.name == "gradle"
            }
        if (plugins.size != 1) {
            throw GradleException("found ${plugins.size} Chaquopy plugins")
        }
        versionName = plugins[0].version

        val verParsed = versionName!!.split(".").map { it.toInt() }
        versionCode = verParsed[0] * 1000000 +
                      verParsed[1] * 1000 +
                      verParsed[2] * 10

        ndk {
            abiFilters += listOf(
                "arm64-v8a", "armeabi-v7a", "x86", "x86_64"
            )
        }

        // Remove other languages imported from Android support libraries.
        resourceConfigurations += "en"
    }

    // Chaquopy generates extra internal-use constructors on static proxy classes.
    lint {
        disable += "ValidFragment"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }
    kotlinOptions {
        jvmTarget = "1.8"
    }

    // For testing with minifyEnabled (see release/README.md).
    buildTypes {
        create("releaseMinify") {
            initWith(getByName("release"))
            isMinifyEnabled = true
            proguardFiles(
                getDefaultProguardFile("proguard-android.txt"),
                "proguard-rules.pro"
            )
        }
    }

    val keystore = file("../chaquo.jks")
    if (keystore.exists()) {
        val config = signingConfigs.create("config") {
            storeFile = keystore
            keyAlias = "key0"
            keyPassword = "android"
            storePassword = "android"
        }
        buildTypes.all { signingConfig = config }
    }
}

chaquopy {
    defaultConfig {
        // Android UI demo
        pip {
            install("Pygments==2.2.0")  // Also used in Java API demo
        }
        staticProxy("chaquopy.demo.ui_demo")

        // Python unit tests
        pip {
            // We use an old version of murmurhash (built from the Chaquopy branch
            // `murmurhash-0`), because in newer versions, importing murmurhash
            // automatically imports and extracts murmurhash/mrmr.so, which would
            // complicate the tests.
            install("murmurhash==0.28.0")  // Requires chaquopy-libcxx

            // Because we set pyc.src to false, we must test extractPackages via pip.
            install("../../product/gradle-plugin/src/test/integration/data/" +
                    "ExtractPackages/change_1/app/extract_packages")
        }
        extractPackages("ep_bravo", "ep_charlie.one")
        staticProxy("chaquopy.test.static_proxy.basic",
                    "chaquopy.test.static_proxy.header",
                    "chaquopy.test.static_proxy.method")
        pyc {
            // For testing bytecode compilation on device, and also to include test
            // source code in stack traces.
            src = false

            // For testing bytecode compilation during build.
            pip = true
        }
    }
}

for (path in listOf(
    "../../product/runtime/src/test",   // Unit tests
    "src/utils"                         // Files shared with pkgtest app
)) {
    android.sourceSets.getByName("main") {
        java { srcDir("$path/java") }
        res { srcDir("$path/res") }
    }
    chaquopy.sourceSets.getByName("main") {
        srcDir("$path/python")
    }
}

dependencies {
    // appcompat version 1.2.0 is required to fix an incompatibility with WebView on API level
    // 21 (https://stackoverflow.com/questions/41025200).
    implementation("androidx.appcompat:appcompat:1.2.0-beta01")
    implementation("androidx.constraintlayout:constraintlayout:1.1.3")
    implementation("androidx.lifecycle:lifecycle-extensions:2.1.0")
    implementation("androidx.preference:preference:1.1.1")
    implementation("junit:junit:4.13.2")
}
