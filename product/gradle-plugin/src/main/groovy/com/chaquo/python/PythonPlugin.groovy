package com.chaquo.python

import org.gradle.api.*
import org.gradle.api.artifacts.Configuration
import org.gradle.api.file.*
import org.gradle.api.plugins.*
import org.gradle.util.*
import org.json.*

import java.nio.file.*
import java.security.MessageDigest

import static java.nio.file.StandardCopyOption.*


class PythonPlugin implements Plugin<Project> {
    static final def NAME = "python"
    static final def MIN_ANDROID_PLUGIN_VER = VersionNumber.parse("2.3.0")
    static final def MAX_TESTED_ANDROID_PLUGIN_VER = VersionNumber.parse("3.1.2")

    Project project
    Object android
    File genDir

    public void apply(Project p) {
        project = p
        genDir = new File(project.buildDir, "generated/$NAME")

        if (!project.hasProperty("android")) {
            throw new GradleException("project.android not set. Did you apply plugin " +
                                              "com.android.application before com.chaquo.python?")
        }
        android = project.android
        checkAndroidPluginVersion()

        extendAaptOptions()
        extendProductFlavor(android.defaultConfig).setDefaults()
        android.productFlavors.all { extendProductFlavor(it) }
        extendSourceSets()
        setupDependencies()
        project.afterEvaluate { afterEvaluate() }
    }

    void checkAndroidPluginVersion() {
        final def ADVICE = "please edit com.android.tools.build:gradle in the buildscript block."
        def depVer = null
        for (dep in project.rootProject.buildscript.configurations.getByName("classpath")
                .getAllDependencies()) {
            if (dep.group == "com.android.tools.build"  &&  dep.name == "gradle") {
                depVer = VersionNumber.parse(dep.version)
                if (depVer < MIN_ANDROID_PLUGIN_VER) {
                    throw new GradleException("This version of Chaquopy requires Android Gradle " +
                                              "plugin version $MIN_ANDROID_PLUGIN_VER or later: " +
                                              ADVICE)
                }
                if (depVer > MAX_TESTED_ANDROID_PLUGIN_VER) {
                    println("Warning: This version of Chaquopy has not been tested with Android " +
                            "Gradle plugin versions beyond $MAX_TESTED_ANDROID_PLUGIN_VER. If you " +
                            "experience problems, " + ADVICE)
                }
                break;
            }
        }
        if (depVer == null) {
            println("Warning: Chaquopy was unable to determine the Android Gradle plugin " +
                    "version. Supported versions are $MIN_ANDROID_PLUGIN_VER to " +
                    "$MAX_TESTED_ANDROID_PLUGIN_VER. If you experience problems with a different " +
                    "version, " + ADVICE)
        }
    }

    // For extraction performance, we want to avoid compressing our .zip files a second time,
    // but .zip is not one of the default noCompress extensions (frameworks/base/tools/aapt/Package.cpp
    // and tools/base/build-system/builder/src/main/java/com/android/builder/packaging/PackagingUtils.java).
    // We don't want to set noCompress "zip" because the user might have an uncompressed .zip
    // which they were relying on the APK to compress.
    //
    // Luckily this option works just as well with entire filenames. Unluckily, it replaces the
    // existing list rather than adds to it, so if we only called noCompress now, it would be lost
    // if the build.gradle used it as well. afterEvaluate is too late to do this, as the Android
    // plugin's own afterEvaluate has already been run by that point and it's copied the noCompress
    // settings elsewhere.
    void extendAaptOptions() {
        def ao = android.aaptOptions

        def originalSet = ao.getClass().getMethod("noCompress", [String[].class] as Class[])
        def newSet = {String... nc ->
            def mergedNc = [Common.ASSET_APP, Common.ASSET_BOOTSTRAP,
                            Common.ASSET_REQUIREMENTS(Common.ABI_COMMON),
                            Common.ASSET_STDLIB]
            for (abi in Common.ABIS) {
                mergedNc.add(Common.ASSET_REQUIREMENTS(abi))
                mergedNc.add("${abi}.zip")  // stdlib-native
            }
            mergedNc.addAll(nc)
            originalSet.invoke(ao, [mergedNc as String[]] as Object[])
        }
        ao.metaClass.noCompress = newSet

        // It also defines a 1-argument overload for some reason. (The metaclass assignment operator
        // will create overloads if closure parameter types are different.)
        ao.metaClass.noCompress = { String nc -> newSet(nc) }

        // We don't currently override setNoCompress to handle `=` notation. Unlike elsewhere in
        // the Android plugin, it doesn't accept an Iterable, only a single String or a String[]
        // array, which would require the syntax `[...] as String[]`. I tried overriding it to
        // support this anyway, but the array somehow got passed straight through as if it was a
        // String, ignoring the parameter type declarations on the closures.
        //
        // From searches I couldn't find an example of anyone actualy using `=` notation here, so
        // the current situation is probably fine. However, we'll check and display a warning just
        // in case.
        project.afterEvaluate {
            if (! ao.noCompress.contains(Common.ASSET_APP)) {
                println("Warning: aaptOptions.noCompress has been overridden: this may reduce " +
                        "Chaquopy performance. Consider replacing `noCompress =` with simply " +
                        "`noCompress`.")
            }
        }

        // Set initial state.
        ao.noCompress()
    }

    PythonExtension extendProductFlavor(ExtensionAware ea) {
        def python = new PythonExtension()
        ea.extensions.add(NAME, python)
        return python
    }

    // TODO #5341: support setRoot
    void extendSourceSets() {
        android.sourceSets.all { sourceSet ->
            sourceSet.metaClass.pyDirSet = sourceSet.java.getClass().newInstance(
                [sourceSet.displayName + " Python source", project] as Object[])
            sourceSet.metaClass.getPython = { return pyDirSet }
            sourceSet.metaClass.python = { closure ->
                closure.delegate = pyDirSet
                closure()
            }
            sourceSet.python.srcDirs = ["src/$sourceSet.name/python"]
        }
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
            python.mergeFrom(android.defaultConfig.python)
            for (flavor in variant.getProductFlavors().reverse()) {
                python.mergeFrom(flavor.python)
            }

            if (variant.mergedFlavor.minSdkVersion.apiLevel < Common.MIN_SDK_VERSION) {
                throw new GradleException("$variant.name: Chaquopy requires minSdkVersion " +
                                          "$Common.MIN_SDK_VERSION or higher.")
            }
            if (python.version == null) {
                throw new GradleException("$variant.name: python.version not set: you may want to " +
                                          "add it to defaultConfig.")
            }
            if (! Common.PYTHON_VERSIONS.contains(python.version)) {
                throw new GradleException("$variant.name: invalid python.version '${python.version}'. " +
                                          "Current versions are ${Common.CURRENT_PYTHON_VERSIONS}.")
            }
            if (! Common.CURRENT_PYTHON_VERSIONS.contains(python.version)) {
                println("Warning: $variant.name: python.version ${python.version} does not " +
                        "contain all current Chaquopy features and bug fixes. Please switch to " +
                        "one of the following versions as soon as possible: " +
                        "${Common.CURRENT_PYTHON_VERSIONS}.")
            }

            createConfigs(variant, python)
            Task reqsTask = createReqsTask(variant, python, buildPackagesTask)
            Task mergeSrcTask = createMergeSrcTask(variant, python)
            createProxyTask(variant, python, buildPackagesTask, reqsTask, mergeSrcTask)
            Task ticketTask = createTicketTask(variant)
            createAssetsTasks(variant, python, reqsTask, mergeSrcTask, ticketTask)
            createJniLibsTasks(variant, python)
        }
    }

    void createConfigs(variant, PythonExtension python) {
        def stdlibConfig = configName(variant, "targetStdlib")
        project.configurations.create(stdlibConfig)
        project.dependencies.add(stdlibConfig,
                                 targetDependency(python.version,
                                                  python.pyc.stdlib ? "stdlib-pyc" : "stdlib"))

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
        def buildNo = Common.PYTHON_BUILD_NUMBERS.get(version)
        return "com.chaquo.python:target:$version-$buildNo:$classifier@zip"
    }

    String[] getAbis(variant) {
        // variant.getMergedFlavor returns a DefaultProductFlavor base class object, which, perhaps
        // by an oversight, doesn't contain the NDK options.
        def abis = new TreeSet<String>()
        def ndk = android.defaultConfig.ndkConfig
        if (ndk.abiFilters) {
            abis.addAll(ndk.abiFilters)  // abiFilters is a HashSet, so its order is undefined.
        }
        for (flavor in variant.getProductFlavors().reverse()) {
            ndk = flavor.ndkConfig
            if (ndk.abiFilters) {
                // Replicate the accumulation behaviour of MergedNdkConfig.append
                abis.addAll(ndk.abiFilters)
            }
        }
        if (abis.isEmpty()) {
            // The Android plugin doesn't make abiFilters compulsory, but we will, because
            // adding every single ABI to the APK is not something we want to do by default.
            throw new GradleException("$variant.name: Chaquopy requires ndk.abiFilters: " +
                                       "you may want to add it to defaultConfig.")
        }
        return abis.toArray()
    }

    Task createBuildPackagesTask() {
        // pip by default finds the cacert file using a path relative to __file__, which won't work
        // when __file__ is something like path/to/a.zip/path/to/module.py. It's easier to run
        // directly from the ZIP and extract the cacert file, than it is to extract the entire ZIP
        // and then deal with auto-generated pyc files complicating the up-to-date checks.
        return project.task("extractPythonBuildPackages") {
            ext.buildPackagesZip = "$genDir/build-packages.zip"
            def cacertRelPath = "pip/_vendor/certifi/cacert.pem"
            ext.cacertPem = "$genDir/$cacertRelPath"
            outputs.files(buildPackagesZip, cacertPem)
            doLast {
                extractResource("gradle/build-packages.zip", genDir)
                // Remove existing directory, otherwise failure to extract will go unnoticed if a
                // previous file still exists.
                project.delete("$genDir/${cacertRelPath.split("/")[0]}")
                project.copy {
                    from project.zipTree(buildPackagesZip)
                    include cacertRelPath
                    into genDir
                }
            }
        }
    }

    Task createReqsTask(variant, PythonExtension python, Task buildPackagesTask) {
        return project.task(taskName("generate", variant, "requirements")) {
            ext.destinationDir = variantGenDir(variant, "requirements")
            dependsOn buildPackagesTask
            inputs.property("python", python.serialize())
            inputs.files(getConfig(variant, "targetAbis"))
            def reqsArgs = []
            for (req in python.pip.reqs) {
                reqsArgs.addAll(["--req", req])
                if (project.file(req).exists()) {
                    inputs.files(req)
                }
            }
            for (reqFile in python.pip.reqFiles) {
                reqsArgs.addAll(["--req-file", reqFile])
                inputs.files(reqFile)
            }
            outputs.dir(destinationDir)
            doLast {
                project.delete(destinationDir)
                project.mkdir(destinationDir)
                def abis = getAbis(variant)
                if (reqsArgs.isEmpty()) {
                    // Subdirectories must exist, or their ZIPs won't be created.
                    project.mkdir("$destinationDir/common")
                    for (abi in abis) {
                        project.mkdir("$destinationDir/$abi")
                    }
                } else {
                    def pythonAbi = Common.PYTHON_ABIS.get(python.versionShort)
                    execBuildPython(python, buildPackagesTask) {
                        args "-m", "chaquopy.pip_install"
                        args "--target", destinationDir
                        args "--android-abis"
                        args abis
                        args reqsArgs
                        args "--"
                        args "--chaquopy", getClass().getPackage().getImplementationVersion()
                        args "--isolated"
                        args "--disable-pip-version-check"
                        args "--cert", buildPackagesTask.cacertPem
                        args "--extra-index-url", "https://chaquo.com/pypi-2.1"
                        args "--only-binary", ":all:"
                        args "--implementation", pythonAbi.substring(0, 2)
                        args "--python-version", pythonAbi.substring(2, 4)
                        args "--abi", pythonAbi
                        args "--no-compile"
                        args python.pip.options
                    }
                }
            }
        }
    }

    Task createMergeSrcTask(variant, PythonExtension python) {
        // Create the main source set directory if it doesn't already exist, to invite the user
        // to put things in it.
        for (dir in android.sourceSets.main.python.srcDirs) {
            project.mkdir(dir)
        }

        // Avoid merge in the common case where there's only one source directory.
        def dirSets = (variant.sourceSets.collect { it.python }
                       .findAll { ! it.sourceFiles.isEmpty() })
        def needMerge = ! (dirSets.size() == 1 &&
                           dirSets[0].srcDirs.size() == 1 &&
                           dirSets[0].filter.excludes.isEmpty() &&
                           dirSets[0].filter.includes.isEmpty())

        def mergeDir = variantGenDir(variant, "sources")
        return project.task(taskName("merge", variant, "sources")) {
            ext.destinationDir = needMerge ? mergeDir : dirSets[0].srcDirs.asList()[0]
            inputs.files(dirSets.collect { it.srcDirs })
            outputs.dir(destinationDir)
            doLast {
                project.delete(mergeDir)
                project.mkdir(mergeDir)
                if (! needMerge) return
                project.copy {
                    into mergeDir
                    exclude "**/*.pyc", "**/*.pyo"
                    duplicatesStrategy "fail"
                    for (dirSet in dirSets) {
                        for (File srcDir in dirSet.srcDirs) {
                            from(srcDir) {
                                excludes = dirSet.filter.excludes
                                includes = dirSet.filter.includes
                            }
                        }
                    }
                    // Allow duplicates for empty files (e.g. __init__.py)
                    eachFile { FileCopyDetails fcd ->
                        if (fcd.file.length() == 0) {
                            def destFile = new File("$mergeDir/$fcd.path")
                            if (destFile.exists() && destFile.length() == 0) {
                                fcd.duplicatesStrategy = DuplicatesStrategy.INCLUDE
                            }
                        }
                    }
                }
            }
        }
    }

    void createProxyTask(variant, PythonExtension python, Task buildPackagesTask, Task reqsTask,
                          Task mergeSrcTask) {
        File destinationDir = variantGenDir(variant, "proxies")
        Task proxyTask = project.task(taskName("generate", variant, "proxies")) {
            inputs.files(buildPackagesTask, reqsTask, mergeSrcTask)
            inputs.property("python", python.serialize())
            outputs.dir(destinationDir)
            doLast {
                project.delete(destinationDir)
                project.mkdir(destinationDir)
                if (!python.staticProxy.isEmpty()) {
                    execBuildPython(python, buildPackagesTask) {
                        args "-m", "chaquopy.static_proxy"
                        args "--path", (mergeSrcTask.destinationDir.toString() +
                                        File.pathSeparator +
                                        "$reqsTask.destinationDir/common")
                        args "--java", destinationDir
                        args python.staticProxy
                    }
                }
            }
        }
        variant.registerJavaGeneratingTask(proxyTask, destinationDir)
    }

    void execBuildPython(PythonExtension python, Task buildPackagesTask, Closure closure) {
        try {
            project.exec {
                environment "PYTHONPATH", buildPackagesTask.buildPackagesZip
                executable python.buildPython
                closure.delegate = delegate
                closure()
            }
        } catch (Exception e) {
            // A failed build in Android Studio 2.3 or 3.0 brings up the Messages window, which
            // shows only the stderr output of the task.
            //
            // Android Studio 3.1 brings up the Build window, which, if in tree mode (the default),
            // initially has the root node focused. This displays only the message of the lowest-
            // level exception in the chain, which will be something like "Process 'command
            // 'python'' finished with non-zero exit value 1".
            //
            // Either way, we need to tell the user how to see the full pip output. Don't change the
            // message depending on the Android Gradle plugin version, because that isn't
            // necessarily the same as the Android Studio version.
            throw new GradleException(
                "buildPython failed ($e). For full details:\n" +
                "* In Android Studio 3.1 and later, open the 'Build' window and switch to text " +
                "mode with the 'ab' button on the left.\n" +
                 "* In Android Studio 3.0 and earlier, open the 'Gradle Console' window.")
        }
    }

    // No ticket is represented as an empty file rather than a missing one. This saves us
    // from having to delete the extracted copy if the app is updated to remove the ticket.
    // (We could pass the ticket to the runtime in some other way, but that would be more
    // complicated.)
    Task createTicketTask(variant) {
        def localProps = new Properties()
        def propsStream = project.rootProject.file('local.properties').newInputStream()
        localProps.load(propsStream)
        propsStream.close()  // Otherwise the Gradle daemon may keep the file in use indefinitely.

        // null input properties give a warning in Gradle 4.4 (Android Studio 3.1). Luckily we're
        // no longer using the empty string to mean anything special.
        def key = localProps.getProperty("chaquopy.license", "")

        return assetTask(variant, "license") {
            inputs.property("app", variant.applicationId)
            inputs.property("key", key)
            doLast {
                def ticket = "";
                if (key.length() > 0) {
                    final def TIMEOUT = 10000
                    def url = ("https://chaquo.com/license/get_ticket" +
                               "?app=$variant.applicationId&key=$key")
                    def connection = (HttpURLConnection) new URL(url).openConnection()
                    connection.setConnectTimeout(TIMEOUT)
                    connection.setReadTimeout(TIMEOUT)
                    def code = connection.getResponseCode()
                    if (code == connection.HTTP_OK) {
                        ticket = connection.getInputStream().getText();
                    } else {
                        throw new GradleException(connection.getErrorStream().getText())
                    }
                }
                project.file("$assetDir/$Common.ASSET_TICKET").write(ticket);
            }
        }
    }

    void createAssetsTasks(variant, python, Task reqsTask, Task mergeSrcTask, Task ticketTask) {
        def excludes = "**/*.pyc **/*.pyo"

        def appAssetsTask = assetTask(variant, "app") {
            inputs.files(mergeSrcTask)
            doLast {
                project.ant.zip(basedir: mergeSrcTask.destinationDir, excludes: excludes,
                                destfile: "$assetDir/$Common.ASSET_APP", whenempty: "create")
            }
        }
        def reqsAssetsTask = assetTask(variant, "requirements") {
            inputs.files(reqsTask)
            doLast {
                for (subdir in reqsTask.destinationDir.listFiles()) {
                    project.ant.zip(basedir: subdir, excludes: excludes, whenempty: "create",
                                    destfile: "$assetDir/${Common.ASSET_REQUIREMENTS(subdir.name)}")
                }
            }
        }
        // TODO: Use same filename pattern for stdlib and bootstrap as we do for requirements.
        def miscAssetsTask = assetTask(variant, "misc") {
            def stdlibConfig = getConfig(variant, "targetStdlib")
            def abiConfig = getConfig(variant, "targetAbis")
            inputs.files(stdlibConfig, abiConfig)
            doLast {
                project.copy {
                    from stdlibConfig
                    into assetDir
                    rename { Common.ASSET_STDLIB }
                }
                extractResource("runtime/$Common.ASSET_BOOTSTRAP", assetDir)

                // The following stdlib native modules are needed during bootstrap and are
                // pre-extracted; all others are loaded from a .zip using AssetFinder.
                def BOOTSTRAP_NATIVE_STDLIB = ["_ctypes.so", "select.so"]
                for (art in abiConfig.resolvedConfiguration.resolvedArtifacts) {
                    def abi = art.classifier
                    project.copy {
                        from project.zipTree(art.file)
                        include "lib-dynload/**"
                        into assetDir
                    }
                    project.ant.zip(basedir: "$assetDir/lib-dynload/$abi",
                                    destfile: "$assetDir/$Common.ASSET_STDLIB_NATIVE/${abi}.zip",
                                    excludes: BOOTSTRAP_NATIVE_STDLIB.join(" "), whenempty: "fail")

                    // extend_path is called in runtime/src/main/python/java/__init__.py
                    def bootstrapDir = "$assetDir/$Common.ASSET_BOOTSTRAP_NATIVE/$abi"
                    extractResource("runtime/lib-dynload/$python.versionShort/$abi/java/chaquopy.so",
                                    "$bootstrapDir/java")
                    new File("$bootstrapDir/java/__init__.py").text = ""

                    project.copy {
                        from "$assetDir/lib-dynload/$abi"
                        into bootstrapDir
                        include BOOTSTRAP_NATIVE_STDLIB
                    }
                    project.delete("$assetDir/lib-dynload")
                }
                extractResource(Common.ASSET_CACERT, assetDir)
            }
        }
        assetTask(variant, "build") {
            inputs.property("python", python.serialize())
            inputs.files(ticketTask, appAssetsTask, reqsAssetsTask, miscAssetsTask)
            doLast {
                def buildJson = new JSONObject()
                buildJson.put("version", python.version)
                buildJson.put("assets", hashAssets(ticketTask, appAssetsTask, reqsAssetsTask,
                                                   miscAssetsTask))
                buildJson.put("extractPackages", new JSONArray(python.extractPackages))
                project.file("$assetDir/$Common.ASSET_BUILD_JSON").text = buildJson.toString(4)
            }
        }
    }

    Task assetTask(variant, String name, Closure closure) {
        def assetBaseDir = variantGenDir(variant, "assets")
        def t = project.task(taskName("generate", variant, "${name}Assets")) {
            ext.destinationDir = "$assetBaseDir/$name"
            ext.assetDir = "$destinationDir/$Common.ASSET_DIR"
            outputs.dir(destinationDir)
            doLast {
                project.delete(destinationDir)
                project.mkdir(assetDir)
            }
        }
        closure.delegate = t
        closure()
        extendMergeTask(variant.getMergeAssets(), t)
        return t
    }

    JSONObject hashAssets(Task... tasks) {
        def assetsJson = new JSONObject()
        def digest = MessageDigest.getInstance("SHA-1")
        for (t in tasks) {
            hashAssets(assetsJson, digest, project.file("$t.destinationDir/$Common.ASSET_DIR"), "")
        }
        return assetsJson
    }

    void hashAssets(JSONObject assetsJson, MessageDigest digest, File dir, String prefix) {
        for (file in dir.listFiles()) {
            def path = prefix + file.name
            if (file.isDirectory()) {
                hashAssets(assetsJson, digest, file, path + "/")
            } else {
                digest.reset()
                assetsJson.put(path, digest.digest(file.bytes).encodeHex())
            }
        }
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
                    extractResource("runtime/jniLibs/$python.versionShort/$abi/libchaquopy_java.so",
                                    "$libsDir/$abi")
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


class PythonExtension extends BaseExtension {
    static final def DEFAULT_EXTRACT_PACKAGES = ["certifi", "sklearn.datasets"]

    String version
    String buildPython
    Set<String> staticProxy = new TreeSet<>()
    Set<String> extractPackages = new TreeSet<>()
    PipExtension pip = new PipExtension()
    PycExtension pyc = new PycExtension()

    void setDefaults() {
        // There is no default version: the user must specify it.
        buildPython = "python"
        extractPackages.addAll(DEFAULT_EXTRACT_PACKAGES)
        pip.setDefaults()
        pyc.setDefaults()
    }

    String getVersionShort() {
        return Common.pyVersionShort(version)
    }

    void version(String v)                      { version = v }
    void buildPython(String bp)                 { buildPython = bp }
    void staticProxy(String... modules)         { staticProxy.addAll(modules) }
    void extractPackages(String... packages)    { extractPackages.addAll(packages) }
    void pip(Closure closure)                   { applyClosure(pip, closure) }
    void pyc(Closure closure)                   { applyClosure(pyc, closure) }

    void mergeFrom(PythonExtension overlay) {
        version = chooseNotNull(overlay.version, version)
        buildPython = chooseNotNull(overlay.buildPython, buildPython)
        staticProxy.addAll(overlay.staticProxy)
        extractPackages.addAll(overlay.extractPackages)
        pip.mergeFrom(overlay.pip)
        pyc.mergeFrom(overlay.pyc)
    }

    // Removed in 0.6.0
    void pipInstall(String... args) {
        throw new GradleException("'pipInstall' has been removed: use 'pip { install ... }' " +
                                  "or 'pip { options ... }' instead")
    }
}


class PipExtension extends BaseExtension {
    List<String> reqs = new ArrayList<>();
    List<String> reqFiles = new ArrayList<>();
    List<String> options = new ArrayList<>();

    void install(String... args) {
        if (args.length == 1) {
            reqs.add(args[0])
        } else if (args.length == 2  &&  args[0].equals("-r")) {
            reqFiles.add(args[1])
        } else {
            throw new GradleException("Invalid python.pip.install format: '" + args.join(" ") + "'")
        }
    }

    void options (String... args) {
        options.addAll(Arrays.asList(args))
    }

    void mergeFrom(PipExtension overlay) {
        reqs.addAll(overlay.reqs)
        reqFiles.addAll(overlay.reqFiles)
        options.addAll(overlay.options)
    }
}


class PycExtension extends BaseExtension {
    Boolean stdlib

    void setDefaults() {
        stdlib = true
    }

    void stdlib(boolean s) { stdlib = s }

    void mergeFrom(PycExtension overlay) {
        stdlib = chooseNotNull(overlay.stdlib, stdlib)
    }
}


class BaseExtension implements Serializable {
    void setDefaults() {}

    static void applyClosure(BaseExtension be, Closure closure) {
        closure.delegate = be
        closure()
    }

    static <T> T chooseNotNull(T overlay, T base) {
        return overlay != null ? overlay : base
    }

    // Using custom classes as task input properties doesn't work in Gradle 2.14.1 / Android
    // Studio 2.2 (https://github.com/gradle/gradle/issues/784), so we use a String as the input
    // property instead. We don't use a byte[] because this version of Gradle apparently compares
    // all properties using equals(), which only checks array identity, not content.
    //
    // This approach also avoids the need for equals and hashCode methods
    // (https://github.com/gradle/gradle/pull/962).
    String serialize() {
        ByteArrayOutputStream baos = new ByteArrayOutputStream()
        ObjectOutputStream oos = new ObjectOutputStream(baos)
        oos.writeObject(this)
        oos.close()
        return escape(baos.toByteArray())
    }

    static String escape(byte[] data) {
        StringBuilder cbuf = new StringBuilder();
        for (byte b : data) {
            if (b >= 0x20 && b <= 0x7e) {
                cbuf.append((char) b);
            } else {
                cbuf.append(String.format("\\x%02x", b & 0xFF));
            }
        }
        return cbuf.toString();
    }
}
