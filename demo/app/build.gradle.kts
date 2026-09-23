import com.android.build.api.dsl.ManagedVirtualDevice.PageAlignment

plugins {
    id("com.android.application")
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
    compileSdk = 36

    defaultConfig {
        applicationId = "com.chaquo.python.demo3"
        minSdk = 24
        targetSdk = 36

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

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    androidResources {
        localeFilters += "en"
    }

    // Chaquopy generates extra internal-use constructors on static proxy classes.
    lint {
        disable += "ValidFragment"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }

    testOptions {
        managedDevices {
            localDevices {
                for (bits in listOf("32", "64")) {
                    create("minVersion$bits") {
                        device = "Small Phone"

                        // Managed devices have a minimum API level of 27.
                        apiLevel = Math.max(27, defaultConfig.minSdk!!)
                        systemImageSource = "default"
                        require64Bit = (bits == "64")
                    }

                    create("maxVersion$bits") {
                        device = "Small Phone"
                        apiLevel = defaultConfig.targetSdk!!
                        systemImageSource = "google_apis"
                        require64Bit = (bits == "64")
                        if (bits == "64") {
                            pageAlignment = PageAlignment.FORCE_16KB_PAGES
                        }
                    }
                }
            }
        }
    }

    // For testing with minifyEnabled (see release/README.md).
    buildTypes {
        create("releaseMinify") {
            initWith(getByName("release"))
            isMinifyEnabled = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
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
        version = (findProperty("chaquopy.version") as String?) ?: "3.10"
        android.defaultConfig.ndk {
            val abisProperty = findProperty("chaquopy.abis") as String?
            if (abisProperty != null) {
                abiFilters += (abisProperty.split(Regex("""\s+""")))
            } else {
                abiFilters += listOf("arm64-v8a", "x86_64")
                if (version in listOf("3.10", "3.11")) {
                    abiFilters += listOf("armeabi-v7a", "x86")
                }
            }
        }

        // Android UI demo
        pip {
            install("Pygments==2.13.0")  // Also used in Java API demo
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
        java { directories.add("$path/java") }
        kotlin { directories.add("$path/java") }
        res { directories.add("$path/res") }
    }
    chaquopy.sourceSets.getByName("main") {
        srcDir("$path/python")
    }
}

dependencies {
    // Keep these versions the same as the pkgtest app.
    implementation("androidx.appcompat:appcompat:1.7.1")
    implementation("androidx.constraintlayout:constraintlayout:1.1.3")
    implementation("androidx.lifecycle:lifecycle-extensions:2.1.0")
    implementation("androidx.preference:preference:1.1.1")
    implementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.1.5")
    androidTestImplementation("androidx.test:rules:1.5.0")
}
