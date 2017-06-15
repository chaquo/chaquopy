package com.chaquo.python

import org.gradle.api.*
import org.gradle.api.artifacts.Configuration
import org.gradle.api.file.*
import org.gradle.api.plugins.*
import org.gradle.util.*

import java.nio.file.*

import static java.nio.file.StandardCopyOption.*


class PythonPlugin implements Plugin<Project> {
    static final def NAME = "python"
    static final def MIN_ANDROID_PLUGIN_VER = VersionNumber.parse("2.3.0")  // TODO #5144
    static final def MAX_TESTED_ANDROID_PLUGIN_VER = VersionNumber.parse("2.3.3")
    static final def MAX_ANDROID_PLUGIN_VER = VersionNumber.parse("3.0.0-alpha1")  // TODO #5180

    Project project
    Object android
    File genDir

    public void apply(Project p) {
        project = p
        genDir = new File(project.buildDir, "generated/$NAME")

        def depVer = null
        for (dep in project.rootProject.buildscript.configurations.getByName("classpath")
                .getAllDependencies()) {
            if (dep.group == "com.android.tools.build"  &&  dep.name == "gradle") {
                depVer = VersionNumber.parse(dep.version)
                if (depVer < MIN_ANDROID_PLUGIN_VER) {
                    throw new GradleException("Chaquopy requires Android Gradle plugin version " +
                                              "$MIN_ANDROID_PLUGIN_VER or later (current version is " +
                                              "$depVer). Please edit the buildscript block.")
                }
                if (depVer >= MAX_ANDROID_PLUGIN_VER) {
                    throw new GradleException("Chaquopy does not work with Android Gradle plugin " +
                                    "version $MAX_ANDROID_PLUGIN_VER or later (current version is " +
                                    "$depVer). Please edit the buildscript block.")
                }
                if (depVer > MAX_TESTED_ANDROID_PLUGIN_VER) {
                    println("Warning: Chaquopy has not been tested with Android Gradle plugin " +
                            "versions beyond $MAX_TESTED_ANDROID_PLUGIN_VER (current version is " +
                            "$depVer). If you experience problems, try editing the " +
                            "buildscript block.")
                }
                break;
            }
        }
        if (depVer == null) {
            println("Warning: Chaquopy was unable to determine the Android Gradle plugin " +
                    "version. Supported versions are $MIN_ANDROID_PLUGIN_VER to " +
                    "$MAX_TESTED_ANDROID_PLUGIN_VER. If you experience problems with a different " +
                    "version, try editing the buildscript block.")
        }

        if (! project.hasProperty("android")) {
            throw new GradleException("project.android not set. Did you apply plugin "+
                                      "com.android.application before com.chaquo.python?")
        }
        android = project.android

        extend(android.defaultConfig)
        /* TODO 5202
        android.productFlavors.whenObjectAdded { extend(it) } */
        // I also tried adding it to buildTypes but it had no effect for some reason

        setupDependencies()

        project.afterEvaluate { afterEvaluate() }
    }

    void extend(ExtensionAware ea) {
        ea.extensions.create(NAME, PythonExtension)
    }

    void setupDependencies() {
        project.repositories { maven { url "https://chaquo.com/maven" } }

        def filename = "chaquopy_java.jar"
        extractResource("runtime/$filename", genDir)
        project.dependencies {
            compile project.files("$genDir/$filename")
        }
    }

    void afterEvaluate() {
        Task buildPackagesTask = createBuildPackagesTask()

        for (variant in android.applicationVariants) {
            def python = new PythonExtension()
            python.mergeFrom(android.defaultConfig)
            /* TODO #5202
            for (flavor in variant.getProductFlavors().reverse()) {
                python.mergeFrom(flavor)
            }
            */
            if (variant.mergedFlavor.minSdkVersion.apiLevel < Common.MIN_SDK_VERSION) {
                throw new GradleException("$variant.name: Chaquopy requires minSdkVersion " +
                                          "$Common.MIN_SDK_VERSION or higher.")
            }
            if (python.version == null) {
                throw new GradleException("$variant.name: python.version not set: you may want to " +
                                          "add it to defaultConfig.")
            }
            if (! Common.PYTHON_VERSIONS.contains(python.version)) {
                throw new GradleException("$variant.name: invalid Python version '${python.version}'. " +
                                          "Available versions are ${Common.PYTHON_VERSIONS}.")
            }

            createConfigs(variant, python)
            /* TODO #5193
            createSourceTasks(variant, python) */
            createAssetsTasks(variant, python, buildPackagesTask)
            createJniLibsTasks(variant, python)
        }
    }

    void createConfigs(variant, PythonExtension python) {
        def stdlibConfig = configName(variant, "targetStdlib")
        project.configurations.create(stdlibConfig)
        project.dependencies.add(stdlibConfig, targetDependency(python.version, "stdlib"))

        def abiConfig = configName(variant, "targetAbis")
        project.configurations.create(abiConfig)
        for (abi in getAbis(variant)) {
            if (! Common.ABIS.contains(abi)) {
                throw new GradleException("$variant.name: Chaquopy does not support the ABI '$abi'. " +
                                          "Supported ABIs are ${Common.ABIS}.")
            }
            project.dependencies.add(abiConfig, targetDependency(python.version, abi))
        }
    }

    Configuration getConfig(variant, name) {
        return project.configurations.getByName(configName(variant, name))
    }

    String targetDependency(String version, String classifier) {
        /** Following the Maven version number format, this is the "build number"
         * (see maven/build.sh). */
        final def TARGET_VERSION_SUFFIX = "-1"
        return "com.chaquo.python:target:$version$TARGET_VERSION_SUFFIX:$classifier@zip"
    }

    Set<String> getAbis(variant) {
        // variant.getMergedFlavor returns a DefaultProductFlavor base class object, which, perhaps
        // by an oversight, doesn't contain the NDK options.
        def abis = new TreeSet<String>()
        if (android.defaultConfig.ndk.abiFilters) {
            abis.addAll(android.defaultConfig.ndk.abiFilters)
        }
        for (flavor in variant.getProductFlavors().reverse()) {
            if (flavor.ndk.abiFilters) {
                /* TODO #5202
                // Replicate the accumulation behaviour of MergedNdkConfig.append
                abis.addAll(flavor.ndk.abiFilters) */
                raise GradleException("$variant.name: Chaquopy does not support per-flavor " +
                                      "abiFilters.")
            }
        }
        if (abis.isEmpty()) {
            // The Android plugin doesn't make abiFilters compulsory, but we will, because
            // adding 25 MB to the APK is not something we want to do by default.
            throw new GradleException("$variant.name: Chaquopy requires ndk.abiFilters: you may want to " +
                                      "add it to defaultConfig.")
        }
        return abis
    }

    /* TODO #5193
    void createSourceTasks(variant, PythonExtension python) {
        File sourceDir = variantGenDir(variant, "source")
        Task genTask = project.task("generatePython${variant.name.capitalize()}Sources") {
            outputs.dir(sourceDir)
            doLast {
                project.delete(sourceDir)
                def pkgDir = "$sourceDir/com/chaquo/python"
                project.mkdir(pkgDir)
                PrintWriter writer = new PrintWriter("$pkgDir/Generated.java")
                writer.println("package com.chaquo.python;")
                writer.println("public class Generated {")
                writer.println("    public void hello() {}")
                writer.println("}")
                writer.close()
            }
        }
        variant.registerJavaGeneratingTask(genTask, sourceDir)
    } */

    Task createBuildPackagesTask() {
        // It's easier to run directly from the ZIP and extract the cacert file, than it is to
        // extract the entire zip and then deal with auto-generated pyc files complicating the
        // up-to-date checks.
        return project.task("extractPythonBuildPackages") {
            ext.buildPackagesZip = "$genDir/build-packages.zip"
            def cacertRelPath = "pip/_vendor/requests/cacert.pem"
            ext.cacertPem = "$genDir/$cacertRelPath"
            outputs.files(buildPackagesZip, cacertPem)
            doLast {
                extractResource("gradle/build-packages.zip", genDir)
                project.copy {
                    from project.zipTree(buildPackagesZip)
                    include cacertRelPath
                    into genDir
                }
            }
        }
    }

    void createAssetsTasks(variant, PythonExtension python, Task buildPackagesTask) {
        Task reqsTask = createReqsTask(variant, python, buildPackagesTask)
        createGenAssetsTask(variant, python, reqsTask)
    }

    Task createReqsTask(variant, PythonExtension python, Task buildPackagesTask) {
        return project.task(taskName("generate", variant, "requirements")) {
            ext.destinationDir = variantGenDir(variant, "requirements")
            dependsOn buildPackagesTask
            inputs.property("python", python)
            outputs.dir(destinationDir)
            doLast {
                project.delete(destinationDir)
                project.mkdir(destinationDir)
                if (!python.pipInstall.isEmpty()) {
                   project.exec {
                       environment "PYTHONPATH", buildPackagesTask.buildPackagesZip
                       executable python.buildPython
                       args "-m", "pip", "install"
                       args "--chaquopy"  // Ensure we never run the system copy of pip by mistake.
                       args "--cert", buildPackagesTask.cacertPem
                       args "--only-binary", ":all:"
                       args "--python-version", Common.pyVersionNoDot(python.version)
                       args "--platform", "android_todo"  // TODO #5215: this should be "android_x86" etc, and
                       args "--implementation", "cp"      //   may need an API level as well like macOS.
                       args "--abi", Common.PYTHON_ABIS.get(python.version)
                       args "--target", destinationDir
                       args python.pipInstall
                   }
                }
            }
        }
    }

    void createGenAssetsTask(variant, python, Task reqsTask) {
        def assetBaseDir = variantGenDir(variant, "assets")
        def assetDir = new File(assetBaseDir, Common.ASSET_DIR)
        def srcDir = project.file("src/main/python")  // TODO #5203 make configurable
        def stdlibConfig = getConfig(variant, "targetStdlib")
        def abiConfig = getConfig(variant, "targetAbis")

        def genTask = project.task(taskName("generate", variant, "assets")) {
            inputs.dir(srcDir)
            inputs.files(reqsTask)
            inputs.files(stdlibConfig, abiConfig)
            outputs.dir(assetBaseDir)
            doLast {
                project.delete(assetBaseDir)
                project.mkdir(assetDir)

                project.mkdir(srcDir)
                project.ant.zip(basedir: srcDir, excludes: "**/*.pyc",
                                destfile: "$assetDir/$Common.ASSET_APP", whenempty: "create")
                project.ant.zip(basedir: reqsTask.destinationDir, excludes: "**/*.pyc",
                                destfile: "$assetDir/$Common.ASSET_REQUIREMENTS", whenempty: "create")

                def artifacts = abiConfig.resolvedConfiguration.resolvedArtifacts
                for (art in artifacts) {    // Stdlib native modules
                    project.copy {
                        from project.zipTree(art.file)
                        include "lib-dynload/**"
                        into assetDir
                    }
                }
                project.copy {              // Stdlib Python modules
                    from(stdlibConfig)
                    into assetDir
                    rename { Common.ASSET_STDLIB }
                }

                extractResource("runtime/$Common.ASSET_CHAQUOPY", assetDir)
                for (abi in getAbis(variant)) {
                    def dynloadJava = "lib-dynload/$abi/java"
                    extractResource("runtime/$dynloadJava/chaquopy.so",
                                    "$assetDir/$dynloadJava")
                    new File("$assetDir/$dynloadJava/__init__.py").createNewFile();
                }
            }
        }
        extendMergeTask(variant.getMergeAssets(), genTask)
    }

    void createJniLibsTasks(variant, PythonExtension python) {
        def libsDir = variantGenDir(variant, "jniLibs")
        def abiConfig = getConfig(variant, "targetAbis")
        def genTask = project.task(taskName("generate", variant, "jniLibs")) {
            inputs.files(abiConfig)
            outputs.dir(libsDir)
            doLast {
                project.delete(libsDir)
                def artifacts = abiConfig.resolvedConfiguration.resolvedArtifacts
                for (art in artifacts) {
                    // Copy jniLibs/<arch>/ in the ZIP to jniLibs/<variant>/<arch>/ in the build
                    // directory. (https://discuss.gradle.org/t/copyspec-support-for-moving-files-directories/7412/1)
                    project.copy {
                        from project.zipTree(art.file)
                        include "jniLibs/**"
                        into libsDir
                        eachFile { FileCopyDetails fcd ->
                            fcd.relativePath = new RelativePath
                                    (!fcd.file.isDirectory(),
                                     fcd.relativePath.segments[1..-1] as String[])
                        }
                        includeEmptyDirs = false
                    }
                }

                for (abi in getAbis(variant)) {
                    extractResource("runtime/jniLibs/$abi/libchaquopy_java.so", "$libsDir/$abi")
                }
            }
        }
        extendMergeTask(project.tasks.getByName("merge${variant.name.capitalize()}JniLibFolders"),
                        genTask)
    }

    void extendMergeTask(Task mergeTask, Task genTask) {
        mergeTask.dependsOn(genTask)
        mergeTask.inputs.files(genTask.outputs)
        mergeTask.doLast {
            project.copy {
                from genTask.outputs
                into mergeTask.outputDir
            }
        }
    }

    File variantGenDir(variant, String type) {
        return new File(genDir, "$type/$variant.dirName")
    }

    String configName(variant, String type) {
        return "$NAME${variant.name.capitalize()}${type.capitalize()}"
    }

    String taskName(String verb, variant, String object) {
        return "$verb${variant.name.capitalize()}${NAME.capitalize()}${object.capitalize()}"
    }

    void extractResource(String name, targetDir) {
        project.mkdir(targetDir)
        def outFile = new File(targetDir, new File(name).name)
        def tmpFile = new File("${outFile.path}.tmp")
        InputStream is = getClass().getResourceAsStream(name)
        if (is == null) {
            throw new IOException("getResourceAsString failed for '$name'")
        }
        Files.copy(is, tmpFile.toPath(), REPLACE_EXISTING)
        project.delete(outFile)
        if (! tmpFile.renameTo(outFile)) {
            throw new IOException("Failed to create '$outFile'")
        }
    }
}


class PythonExtension implements Serializable {
    String version
    String buildPython = "python"
    List<String> pipInstall = new ArrayList<>();

    void pipInstall(String... args) {
        pipInstall.addAll(Arrays.asList(args))
    }

    void mergeFrom(o) {
        PythonExtension overlay = o.python
        version = chooseNotNull(overlay.version, version)
        buildPython = chooseNotNull(overlay.buildPython, buildPython)
        pipInstall.addAll(overlay.pipInstall)
    }

    private static <T> T chooseNotNull(T overlay, T base) {
        return overlay != null ? overlay : base
    }

    // equals() and hashCode() are not required in Gradle 3.5 thanks to
    // https://github.com/gradle/gradle/pull/962, but they're still required in Gradle 3.3, which
    // is used by Android Studio 2.3.
    boolean equals(o) {
        if (this.is(o)) return true
        if (getClass() != o.class) return false

        PythonExtension that = (PythonExtension) o

        if (buildPython != that.buildPython) return false
        if (pipInstall != that.pipInstall) return false
        if (version != that.version) return false

        return true
    }

    int hashCode() {
        int result
        result = (version != null ? version.hashCode() : 0)
        result = 31 * result + buildPython.hashCode()
        result = 31 * result + pipInstall.hashCode()
        return result
    }
}