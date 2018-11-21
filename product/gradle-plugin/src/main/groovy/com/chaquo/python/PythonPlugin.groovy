package com.chaquo.python

import org.gradle.api.*
import org.gradle.api.artifacts.Configuration
import org.gradle.api.file.*
import org.gradle.api.initialization.dsl.ScriptHandler
import org.gradle.api.plugins.*
import org.gradle.process.ExecResult
import org.gradle.util.*
import org.json.*

import java.nio.file.*
import java.security.MessageDigest

import static java.nio.file.StandardCopyOption.*


class PythonPlugin implements Plugin<Project> {
    static final def NAME = "python"
    static final def PLUGIN_VERSION = PythonPlugin.class.package.implementationVersion
    static final def MIN_ANDROID_PLUGIN_VER = VersionNumber.parse("3.0.0")
    static final def MAX_TESTED_ANDROID_PLUGIN_VER = VersionNumber.parse("3.2.1")

    Project project
    ScriptHandler buildscript
    Object android
    VersionNumber androidPluginVer
    File genDir

    public void apply(Project p) {
        project = p
        genDir = new File(project.buildDir, "generated/$NAME")

        // Use the buildscript context to load dependencies so they'll come from the same
        // repository as the Gradle plugin itself.
        buildscript = project.rootProject.buildscript

        if (!project.hasProperty("android")) {
            throw new GradleException("project.android not set. Did you apply plugin " +
                                              "com.android.application before com.chaquo.python?")
        }
        android = project.android
        androidPluginVer = getAndroidPluginVersion()

        extendAaptOptions()
        extendProductFlavor(android.defaultConfig).setDefaults()
        android.productFlavors.all { extendProductFlavor(it) }
        extendSourceSets()
        setupDependencies()
        project.afterEvaluate { afterEvaluate() }
    }

    VersionNumber getAndroidPluginVersion() {
        final def ADVICE =
            "please edit com.android.tools.build:gradle in the top-level build.gradle. See " +
            "https://chaquo.com/chaquopy/doc/current/versions.html."
        def depVer = null
        for (dep in buildscript.configurations.getByName("classpath").getAllDependencies()) {
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
        return depVer
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
            def name = sourceSet.name + " Python source"
            def javaSet = sourceSet.java
            Object[] args = null
            if (androidPluginVer < VersionNumber.parse("3.2.0-alpha01")) {
                args = [name, project]
            } else {
                args = [name, project, javaSet.type, javaSet.dslScope]
            }
            sourceSet.metaClass.pyDirSet = javaSet.getClass().newInstance(args)
            sourceSet.metaClass.getPython = { return pyDirSet }
            sourceSet.metaClass.python = { closure ->
                closure.delegate = pyDirSet
                closure()
            }
            sourceSet.python.srcDirs = ["src/$sourceSet.name/python"]
        }
    }

    void setupDependencies() {
        def runtimeJava = getConfig("runtimeJava")
        buildscript.dependencies.add(runtimeJava.name, runtimeDep("chaquopy_java.jar"))
        project.dependencies {
            // Can't depend directly on runtimeJava, because "Currently you can only declare
            // dependencies on configurations from the same project."
            implementation project.files(runtimeJava)
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
                throw new GradleException(
                    "$variant.name: This version of Chaquopy requires minSdkVersion " +
                    "$Common.MIN_SDK_VERSION or higher. See " +
                    "https://chaquo.com/chaquopy/doc/current/versions.html.")
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
        buildscript.dependencies {
            add(getConfig("runtimePython").name, runtimeDep("bootstrap.zip"))
            add(getConfig("targetStdlib", variant).name,
                targetDep(python.pyc.stdlib ? "stdlib-pyc" : "stdlib"))
        }

        for (abi in getAbis(variant)) {
            if (! Common.ABIS.contains(abi)) {
                throw new GradleException("$variant.name: Chaquopy does not support the ABI " +
                                          "'$abi'. Supported ABIs are ${Common.ABIS}.")
            }
            buildscript.dependencies {
                add(getConfig("runtimeJni", variant).name, runtimeDep("libchaquopy_java.so", abi))
                add(getConfig("runtimeModule", variant).name, runtimeDep("chaquopy.so", abi))
                add(getConfig("targetNative", variant).name, targetDep(abi))
            }
        }
    }

    Configuration getConfig(String name, variant=null) {
        def variantName = (variant != null) ? variant.name : ""
        def configName = "$NAME${variantName.capitalize()}${name.capitalize()}"
        return buildscript.configurations.maybeCreate(configName)
    }

    Object targetDep(String classifier) {
        def version = "${Common.PYTHON_VERSION}-${Common.PYTHON_BUILD_NUM}"
        return "com.chaquo.python:target:$version:$classifier@zip"
    }

    Object runtimeDep(String filename, String classifier=null) {
        def dotPos = filename.lastIndexOf(".")
        def result = [
            group: "com.chaquo.python.runtime",
            name: filename.substring(0, dotPos),
            version: PLUGIN_VERSION,
            ext: filename.substring(dotPos + 1),
        ]
        if (classifier != null) {
            result.put("classifier", classifier)
        }
        return result
    }

    File getNativeArtifact(Configuration config, String abi) {
        return config.resolvedConfiguration.resolvedArtifacts.find {
            it.classifier == abi
        }.file
    }

    List<String> getAbis(variant) {
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
        return new ArrayList(abis)
    }

    Task createBuildPackagesTask() {
        // pip by default finds the cacert file using a path relative to __file__, which won't work
        // when __file__ is something like path/to/a.zip/path/to/module.py. It's easier to run
        // directly from the ZIP and extract the cacert file, than it is to extract the entire ZIP
        // and then deal with auto-generated pyc files complicating the up-to-date checks.
        return project.task("extractPythonBuildPackages") {
            // With Python 2.7 on Windows, zipimport has a maximum path length of about 256
            // characters, including the path of the ZIP file itself. The longest path within
            // the ZIP is currently 66 characters, which means the maximum ZIP file path length
            // is about 190. The integration tests with the longest names get quite close to that,
            // so make the filename as short as possible.
            def zipName = "bp.zip"
            ext.buildPackagesZip = "$genDir/$zipName"
            def cacertRelPath = "pip/_vendor/certifi/cacert.pem"
            ext.cacertPem = "$genDir/$cacertRelPath"
            outputs.files(buildPackagesZip, cacertPem)
            doLast {
                extractResource("gradle/build-packages.zip", genDir, zipName)

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
            def abis = getAbis(variant)
            ext.destinationDir = variantGenDir(variant, "requirements")
            dependsOn buildPackagesTask
            inputs.property("abis", abis)
            inputs.property("buildPython", python.buildPython)
            inputs.property("pip", python.pip.serialize())
            def reqsArgs = []
            for (req in python.pip.reqs) {
                reqsArgs.addAll(["--req", req])
                def semicolonIndex = req.indexOf(";")  // Environment markers
                if (semicolonIndex == -1) {
                    semicolonIndex = req.length()
                }
                def baseReq = req.substring(0, semicolonIndex)
                def reqIsFile = false
                try {  // project.file may throw on an invalid filename.
                    if (project.file(baseReq).exists()) {
                        reqIsFile = true
                    }
                } catch (Exception e) {}
                if (reqIsFile) {
                    inputs.files(baseReq)
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
                if (reqsArgs.isEmpty()) {
                    // Subdirectories must exist, or their ZIPs won't be created.
                    project.mkdir("$destinationDir/common")
                    for (abi in abis) {
                        project.mkdir("$destinationDir/$abi")
                    }
                } else {
                    execBuildPython(python, buildPackagesTask) {
                        args "-m", "chaquopy.pip_install"
                        args "--target", destinationDir
                        args "--android-abis"
                        args abis
                        args reqsArgs
                        args "--"
                        args "--chaquopy", PLUGIN_VERSION
                        args "--isolated"  // Disables config files and environment variables.
                        args "--no-build-isolation"  // I've not yet seen a package which requires
                                                     // this, and it would also require altering
                                                     // build_env.py to keep our modified copy of
                                                     // setuptools on the PYTHONPATH.
                        args "--disable-pip-version-check"
                        args "--cert", buildPackagesTask.cacertPem
                        if (!("--index-url" in python.pip.options ||
                              "-i" in python.pip.options)) {
                            // Treat our extra index URL as an extension of the default one,
                            // so --index-url replaces them both.
                            args "--extra-index-url", "https://chaquo.com/pypi-2.1"
                        }
                        args "--implementation", Common.PYTHON_IMPLEMENTATION
                        args "--python-version", Common.PYTHON_VERSION
                        args "--abi", Common.PYTHON_ABI
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

        def dirSets = (variant.sourceSets.collect { it.python }
                       .findAll { ! it.sourceFiles.isEmpty() })
        def mergeDir = variantGenDir(variant, "sources")
        return project.task(taskName("merge", variant, "sources")) {
            ext.destinationDir = mergeDir
            inputs.files(dirSets.collect { it.sourceFiles })
            outputs.dir(destinationDir)
            doLast {
                project.delete(mergeDir)
                project.mkdir(mergeDir)
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
            inputs.property("buildPython", python.buildPython)
            inputs.property("staticProxy", python.staticProxy)
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
        final def ADVICE = "set python.buildPython to your Python executable path."
        ExecResult execResult = null
        try {
            execResult = project.exec {
                environment "PYTHONPATH", buildPackagesTask.buildPackagesZip
                python.buildPython.split(/\s+/).eachWithIndex { word, i ->
                    if (i == 0) {
                        executable word
                    } else {
                        args word
                    }
                }
                args "-S"  // Avoid interference from system/user site-packages
                           // (this is not inherited by subprocesses).
                ignoreExitValue true  // A missing executable will still throw an exception.
                closure.delegate = delegate
                closure()
            }
        } catch (Exception e) {
            throw new GradleException("'$python.buildPython' failed to start ($e). Please " + ADVICE)
        }
        if (python.buildPython.startsWith("py ") && (execResult.exitValue == 103)) {
            // Before Python 3.6, stderr from the `py` command was lost
            // (https://bugs.python.org/issue25789). This is the only likely error.
            throw new GradleException("'$python.buildPython': could not find the requested " +
                                      "version of Python. Please either install it, or " + ADVICE);
        }
        try {
            execResult.assertNormalExitValue()
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
                makeZip(basedir: mergeSrcTask.destinationDir, excludes: excludes,
                        destfile: "$assetDir/$Common.ASSET_APP", whenempty: "create")
            }
        }
        def reqsAssetsTask = assetTask(variant, "requirements") {
            inputs.files(reqsTask)
            doLast {
                for (subdir in reqsTask.destinationDir.listFiles()) {
                    makeZip(basedir: subdir, excludes: excludes, whenempty: "create",
                            destfile: "$assetDir/${Common.ASSET_REQUIREMENTS(subdir.name)}")
                }
            }
        }
        // TODO: Use same filename pattern for stdlib and bootstrap as we do for requirements.
        def miscAssetsTask = assetTask(variant, "misc") {
            def runtimePython = getConfig("runtimePython")
            def runtimeModule = getConfig("runtimeModule", variant)
            def targetStdlib = getConfig("targetStdlib", variant)
            def targetNative = getConfig("targetNative", variant)
            inputs.files(runtimePython, runtimeModule, targetStdlib, targetNative)
            doLast {
                project.copy {
                    into assetDir
                    from(runtimePython) { rename { Common.ASSET_BOOTSTRAP } }
                    from(targetStdlib) { rename { Common.ASSET_STDLIB } }
                }

                // The following stdlib native modules are needed during bootstrap and are
                // pre-extracted; all others are loaded from a .zip using AssetFinder.
                def BOOTSTRAP_NATIVE_STDLIB = [
                    "_ctypes.so",  // java.primitive and java.android.importer
                    "_struct.so",  // java.android.importer
                    "binascii.so",  // zipfile < java.android.importer
                    "math.so",  // datetime < calendar < java.android.importer
                    "mmap.so",  // elftools < java.android.importer
                    "zlib.so",  // zipimport
                ]

                for (abi in getAbis(variant)) {
                    project.ant.unzip(src: getNativeArtifact(targetNative, abi),
                                      dest: assetDir) {
                        patternset() {
                            include(name: "lib-dynload/**")
                        }
                    }
                    makeZip(basedir: "$assetDir/lib-dynload/$abi",
                            destfile: "$assetDir/$Common.ASSET_STDLIB_NATIVE/${abi}.zip",
                            excludes: BOOTSTRAP_NATIVE_STDLIB.join(" "),
                            whenempty: "fail")

                    // extend_path is called in runtime/src/main/python/java/__init__.py
                    def bootstrapDir = "$assetDir/$Common.ASSET_BOOTSTRAP_NATIVE/$abi"
                    project.copy {
                        into bootstrapDir
                        from("$assetDir/lib-dynload/$abi") {
                            include BOOTSTRAP_NATIVE_STDLIB
                        }
                        from(getNativeArtifact(runtimeModule, abi)) {
                            into "java"
                            rename { "chaquopy.so" }
                        }
                    }
                    new File("$bootstrapDir/java/__init__.py").text = ""
                    project.delete("$assetDir/lib-dynload")
                }
                extractResource(Common.ASSET_CACERT, assetDir)
            }
        }
        assetTask(variant, "build") {
            inputs.property("extractPackages", python.extractPackages)
            inputs.files(ticketTask, appAssetsTask, reqsAssetsTask, miscAssetsTask)
            doLast {
                def buildJson = new JSONObject()
                buildJson.put("assets", hashAssets(ticketTask, appAssetsTask, reqsAssetsTask,
                                                   miscAssetsTask))
                buildJson.put("extractPackages", new JSONArray(python.extractPackages))
                project.file("$assetDir/$Common.ASSET_BUILD_JSON").text = buildJson.toString(4)
            }
        }
    }

    // Takes the same arguments as project.ant.zip, but makes sure the ZIP is reproducible.
    def makeZip(Map args) {
        // We're going to overwrite the timestamps, so make sure we don't accidentally do this
        // to any source files.
        def baseDir = project.file(args.get("basedir")).toString()
        if (!baseDir.startsWith(project.buildDir.toString())) {
            throw new GradleException("$baseDir is not within $project.buildDir")
        }

        // UTF-8 encoding is apparently on by default on Linux and off by default on Windows:
        // this alters the resulting ZIP file even if all filenames are ASCII.
        args.put("encoding", "UTF-8")

        // This timestamp corresponds to 1980-01-00 00:00 UTC, the minimum timestamp a ZIP file
        // can represent. This is also the timestamp the Android Gradle plugin sets on the
        // APK's own members.
        project.fileTree(baseDir).visit { it.file.setLastModified(315532800000) }
        project.ant.zip(args)
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
        def runtimeJni = getConfig("runtimeJni", variant)
        def targetNative = getConfig("targetNative", variant)
        def genTask = project.task(taskName("generate", variant, "jniLibs")) {
            inputs.files(runtimeJni, targetNative)
            outputs.dir(libsDir)
            doLast {
                project.delete(libsDir)
                def artifacts = targetNative.resolvedConfiguration.resolvedArtifacts
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
                    project.copy {
                        from getNativeArtifact(runtimeJni, abi)
                        into "$libsDir/$abi"
                        rename { "libchaquopy_java.so" }
                    }
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

    String taskName(String verb, variant, String object) {
        return "$verb${variant.name.capitalize()}${NAME.capitalize()}${object.capitalize()}"
    }

    void extractResource(String name, targetDir) {
        extractResource(name, targetDir, new File(name).name)
    }

    void extractResource(String name, targetDir, String targetName) {
        project.mkdir(targetDir)
        def outFile = new File(targetDir, targetName)
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
    static final def DEFAULT_EXTRACT_PACKAGES = [
        "certifi",
        "cv2.data",
        "ipykernel",
        "jedi.evaluate",
        "matplotlib",       // Data (mostly fonts) is in a subdirectory "mpl-data", which is
                            // not a valid package name, We could add a patch to rename it and
                            // make this more specific, but it's probably not worth it because
                            // it would still make up a large proportion of the wheel size.
        "nbformat",
        "notebook",
        "obspy",  // Has data directories in many packages.
        "pytz",
        "sklearn.datasets",
        "spacy.data",       // Depends on server/pypi/packages/spacy/patches/data.patch.
        "theano",  // Could maybe make this more specific, but Theano has been abandoned, and
                   // has unacceptable performance without a compiler anyway.
    ]

    String buildPython
    Set<String> staticProxy = new TreeSet<>()
    Set<String> extractPackages = new TreeSet<>()
    PipExtension pip = new PipExtension()
    PycExtension pyc = new PycExtension()

    void setDefaults() {
        // `version` has no default: the user must specify it.
        // `buildPython`'s default depends on the OS and the value of `version`.
        extractPackages.addAll(DEFAULT_EXTRACT_PACKAGES)
        pip.setDefaults()
        pyc.setDefaults()
    }
    
    String getBuildPython() {
        if (this.@buildPython != null) {
            return this.@buildPython
        }
        def targetMajorVer = "3"
        if (System.getProperty("os.name").startsWith("Windows")) {
            // See PEP 397. After running the official Windows installer with default settings, this
            // will be the only Python thing on the PATH.
            return "py -$targetMajorVer"
        } else {
            return "python$targetMajorVer"  // See PEP 394.
        }
    }

    void version(String v) {
        if (v.equals(Common.PYTHON_VERSION)) {
            println("Warning: python.version is no longer required and should be removed.")
        } else {
            throw new GradleException(
                "This version of Chaquopy does not include Python version $v. " +
                "Either remove python.version to use Python $Common.PYTHON_VERSION, or see " +
                "https://chaquo.com/chaquopy/doc/current/versions.html for other options.")
        }
    }
    void buildPython(String bp)                 { buildPython = bp }
    void staticProxy(String... modules)         { staticProxy.addAll(modules) }
    void extractPackages(String... packages)    { extractPackages.addAll(packages) }
    void pip(Closure closure)                   { applyClosure(pip, closure) }
    void pyc(Closure closure)                   { applyClosure(pyc, closure) }

    void mergeFrom(PythonExtension overlay) {
        buildPython = chooseNotNull(overlay.@buildPython, this.@buildPython)
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
