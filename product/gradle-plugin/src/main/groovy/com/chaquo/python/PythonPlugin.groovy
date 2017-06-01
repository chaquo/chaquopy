package com.chaquo.python

import org.gradle.api.*
import org.gradle.api.file.*
import org.gradle.api.plugins.*
import org.gradle.util.*

import java.nio.file.*

import static java.nio.file.StandardCopyOption.*


class PythonPlugin implements Plugin<Project> {
    static final def NAME = "python"
    static final def MIN_ANDROID_PLUGIN_VER = VersionNumber.parse("2.3.0")  // TODO #5144
    static final def MAX_TESTED_ANDROID_PLUGIN_VER = VersionNumber.parse("2.3.0")
    static final def MAX_ANDROID_PLUGIN_VER = VersionNumber.parse("3.0.0-alpha1")  // TODO #5180

    Project project
    Object android

    public void apply(Project project) {
        this.project = project

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
        this.android = project.android

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
        project.repositories { maven { url "http://chaquo.com/maven" } }

        project.delete(pythonGenDir())
        def filename = "chaquopy_java.jar"
        extractResource("runtime/$filename", pythonGenDir())
        project.dependencies {
            compile project.files("${pythonGenDir()}/$filename")
        }
    }

    void afterEvaluate() {
        for (variant in android.applicationVariants) {
            def python = new PythonExtension()
            python.mergeFrom(android.defaultConfig)
            /* TODO #5202
            for (flavor in variant.getProductFlavors().reverse()) {
                python.mergeFrom(flavor)
            }
            */
            if (python.version == null) {
                throw new GradleException("python.version not set for variant '$variant.name'. " +
                                          "You may want to add it to defaultConfig.")
            }
            if (! Common.PYTHON_VERSIONS.contains(python.version)) {
                throw new GradleException("Invalid Python version '${python.version}'. " +
                                          "Available versions are ${Common.PYTHON_VERSIONS}.")
            }

            createTargetConfigs(variant, python)
            /* TODO #5193
            createSourceTask(variant, python) */
            createAssetsTask(variant, python)
            createJniLibsTask(variant, python)
        }
    }

    void createTargetConfigs(variant, PythonExtension python) {
        def stdlibConfig = configName(variant, "targetStdlib")
        project.configurations.create(stdlibConfig)
        project.dependencies.add(stdlibConfig, targetDependency(python.version, "stdlib"))

        def abiConfig = configName(variant, "targetAbis")
        project.configurations.create(abiConfig)
        for (abi in getAbis(variant)) {
            if (! Common.ABIS.contains(abi)) {
                throw new GradleException("Chaquopy does not support the ABI '$abi'. " +
                                          "Supported ABIs are ${Common.ABIS}.")
            }
            project.dependencies.add(abiConfig, targetDependency(python.version, abi))
        }
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
                raise GradleException("Chaquopy does not yet support per-flavor abiFilters.")
            }
        }
        if (abis.isEmpty()) {
            // The Android plugin doesn't make abiFilters compulsory, but we will, because
            // adding 25 MB to the APK is not something we want to do by default.
            throw new GradleException("ndk.abiFilters not set for variant '$variant.name'. " +
                                      "You may want to add it to defaultConfig.")
        }
        return abis
    }

    /* TODO #5193
    void createSourceTask(variant, PythonExtension python) {
        // FIXME python{} parameters may need to be task inputs as well
        // (https://afterecho.uk/blog/create-a-standalone-gradle-plugin-for-android-part-3.html)
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

    void createAssetsTask(variant, PythonExtension python) {
        // FIXME python{} parameters and abiFilters may need to be task inputs as well
        def assetBaseDir = variantGenDir(variant, "assets")
        def assetDir = new File(assetBaseDir, Common.ASSET_DIR)
        def genTask = project.task(genTaskName(variant, "assets")) {
            outputs.files(project.fileTree(assetBaseDir))
            doLast {
                project.delete(assetBaseDir)
                project.copy {
                    from(project.configurations.getByName(configName(variant, "targetStdlib")))
                    into assetDir
                    rename { "stdlib.zip" }
                }

                extractResource("runtime/chaquopy.zip", assetDir)
                for (abi in getAbis(variant)) {
                    def dynloadJava = "lib-dynload/$abi/java"
                    extractResource("runtime/$dynloadJava/chaquopy.so",
                                    "$assetDir/$dynloadJava")
                    new File("$assetDir/$dynloadJava/__init__.py").createNewFile();
                }

                def artifacts = project.configurations.getByName(configName(variant, "targetAbis"))
                        .resolvedConfiguration.resolvedArtifacts
                for (art in artifacts) {
                    project.copy {
                        from project.zipTree(art.file)
                        include "lib-dynload/**"
                        into assetDir
                    }
                }
            }
        }
        extendMergeTask(variant.getMergeAssets(), genTask)
    }

    void createJniLibsTask(variant, PythonExtension python) {
        // FIXME python{} parameters and abiFilters may need to be task inputs as well
        def libsDir = variantGenDir(variant, "jniLibs")
        def genTask = project.task(genTaskName(variant, "jniLibs")) {
            outputs.files(project.fileTree(libsDir))
            doLast {
                project.delete(libsDir)
                def artifacts = project.configurations.getByName(configName(variant, "targetAbis"))
                        .resolvedConfiguration.resolvedArtifacts
                for (art in artifacts) {
                    project.copy {
                        from project.zipTree(art.file)
                        include "jniLibs/**"
                        into libsDir
                        eachFile { FileCopyDetails fcd ->  // https://discuss.gradle.org/t/copyspec-support-for-moving-files-directories/7412/1
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

    File genDir() {
        return new File(project.buildDir, "generated")
    }

    File pythonGenDir() {
        return new File(genDir(), NAME)
    }

    File variantGenDir(variant, String type) {
        return new File(genDir(), "$type/$NAME/$variant.dirName")
    }

    String configName(variant, String type) {
        return "$NAME${variant.name.capitalize()}${type.capitalize()}"
    }

    String genTaskName(variant, String type) {
        return "generate${NAME.capitalize()}${variant.name.capitalize()}${type.capitalize()}"
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


class PythonExtension {
    String version

    void mergeFrom(o) {
        PythonExtension overlay = o.python
        version = chooseNotNull(overlay.version, version);
    }

    private static <T> T chooseNotNull(T overlay, T base) {
        return overlay != null ? overlay : base
    }
}