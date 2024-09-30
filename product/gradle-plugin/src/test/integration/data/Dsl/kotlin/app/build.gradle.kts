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

    flavorDimensions += "variant"
    productFlavors {
        create("property") { dimension = "variant" }
        create("method") { dimension = "variant" }
        create("bpProperty") { dimension = "variant" }
        create("bpMethod") { dimension = "variant" }
    }
}

// defaultConfig properties (all other sub-properties are covered by productFlavors)
chaquopy.defaultConfig.extractPackages += "ep_default_property"

// defaultConfig methods
chaquopy {
    defaultConfig {
        extractPackages("ep_default_method")
    }
}

// productFlavors properties
val p = chaquopy.productFlavors.getByName("property")
p.version = "3.9"
p.extractPackages += "ep_property"
p.staticProxy += "sp_property"
p.pip.install("certifi")
p.pip.options("-c", "constraints-certifi.txt")
p.pyc.src = true
p.pyc.pip = false
p.pyc.stdlib = false

// productFlavors methods
chaquopy {
    productFlavors {
        getByName("method") {
            version = "3.10"
            extractPackages("ep_method")
            staticProxy("sp_method")
            pip {
                install("six")
                options("-c", "constraints-six.txt")
            }
            pyc {
                src = false
                pip = true
                stdlib = false
            }
        }

        // The easiest way to test buildPython is by causing a failure.
        getByName("bpProperty") {
            buildPython = listOf("python-property")
            pyc.src = true
        }
        getByName("bpMethod") {
            buildPython("python-method")
            pyc.src = true
        }

        try {
            getByName("nonexistent")
            throw GradleException("getByName unexpectedly succeeded")
        } catch (e: UnknownDomainObjectException) {}
    }
}

// sourceSets properties
chaquopy.sourceSets.getByName("property").srcDir("src/ss_property")

// sourceSets methods
chaquopy {
    sourceSets {
        getByName("method") {
            srcDir("src/ss_method")
        }

        try {
            getByName("nonexistent")
            throw GradleException("getByName unexpectedly succeeded")
        } catch (e: UnknownDomainObjectException) {}
    }
}
