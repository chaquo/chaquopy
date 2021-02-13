package com.chaquo.python

import org.apache.commons.compress.archivers.zip.*
import org.gradle.api.*
import org.gradle.api.artifacts.Configuration
import org.gradle.api.file.*
import org.gradle.api.initialization.dsl.ScriptHandler
import org.gradle.api.plugins.*
import org.gradle.process.ExecResult
import org.gradle.process.internal.ExecException
import org.gradle.util.*
import org.json.*

import java.nio.file.*
import java.security.MessageDigest

import static com.chaquo.python.Common.assetZip;
import static java.nio.file.StandardCopyOption.*


class PythonPlugin implements Plugin<Project> {
    static final def NAME = "python"
    static final def PLUGIN_VERSION = PythonPlugin.class.package.implementationVersion
    static final def MIN_ANDROID_PLUGIN_VER = VersionNumber.parse("3.4.0")
    static final def MAX_TESTED_ANDROID_PLUGIN_VER = VersionNumber.parse("4.1.2")

    Project project
    ScriptHandler buildscript
    Object android
    boolean isLibrary
    VersionNumber androidPluginVer
    File genDir
    Task buildPackagesTask

    public void apply(Project p) {
        project = p
        genDir = new File(project.buildDir, "generated/$NAME")

        // Use the buildscript context to load dependencies so they'll come from the same
        // repository as the Gradle plugin itself.
        buildscript = project.rootProject.buildscript

        if (!project.hasProperty("android")) {
            throw new GradleException(
                "project.android not set. Did you apply plugin com.android.application or " +
                "com.android.library before com.chaquo.python?")
        }
        android = project.android
        androidPluginVer = getAndroidPluginVersion()
        isLibrary = project.pluginManager.hasPlugin("com.android.library")

        File proguardFile = extractResource("proguard-rules.pro", genDir)
        android.defaultConfig.proguardFile(proguardFile)
        if (isLibrary) {
            android.defaultConfig.consumerProguardFile(proguardFile)
        }
        extendProductFlavor(android.defaultConfig).setDefaults()
        android.productFlavors.all { extendProductFlavor(it) }

        extendSourceSets()
        setupDependencies()
        project.afterEvaluate { afterEvaluate() }
    }

    VersionNumber getAndroidPluginVersion() {
        final def ADVICE =
            "please edit the version of com.android.tools.build:gradle in your top-level " +
            "build.gradle file. See https://chaquo.com/chaquopy/doc/current/versions.html."
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

    PythonExtension extendProductFlavor(ExtensionAware ea) {
        def python = new PythonExtension(project)
        ea.extensions.add(NAME, python)
        return python
    }

    // TODO #5341: support setRoot
    void extendSourceSets() {
        android.sourceSets.all { sourceSet ->
            def name = sourceSet.name + " Python source"
            def javaSet = sourceSet.java
            Object[] args = null
            if (androidPluginVer < VersionNumber.parse("3.6.0-alpha01")) {
                args = [name, project, javaSet.type, javaSet.dslScope]
            } else {
                args = [name, project, javaSet.type]
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
            // Use `api` rather than `implementation` so it's available to dynamic feature
            // modules.
            //
            // Can't depend directly on runtimeJava, because "Currently you can only declare
            // dependencies on configurations from the same project."
            api project.files(runtimeJava)
        }
    }

    void afterEvaluate() {
        buildPackagesTask = createBuildPackagesTask()

        for (variant in (isLibrary ? android.libraryVariants : android.applicationVariants)) {
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
            Task reqsTask = createReqsTask(variant, python)
            Task mergeSrcTask = createMergeSrcTask(variant, python)
            createProxyTask(variant, python, reqsTask, mergeSrcTask)
            Task ticketTask = createTicketTask(variant)
            createAssetsTasks(variant, python, reqsTask, mergeSrcTask, ticketTask)
            createJniLibsTasks(variant, python)
        }
    }

    void createConfigs(variant, PythonExtension python) {
        buildscript.dependencies {
            add(getConfig("runtimePython").name, runtimeDep(assetZip(Common.ASSET_BOOTSTRAP)))
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
                for (name in ["chaquopy", "chaquopy_android"]) {
                    add(getConfig("runtimeModules", variant).name, runtimeDep("${name}.so", abi))
                }
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

    Task createReqsTask(variant, PythonExtension python) {
        return project.task(taskName("generate", variant, "requirements")) {
            def abis = getAbis(variant)
            // Using variantGenDir could cause us to exceed the Windows 260-character filename
            // limit with some packages (e.g. https://github.com/chaquo/chaquopy/issues/164),
            // so use something shorter.
            ext.destinationDir = new File(project.buildDir, "pip/$variant.dirName")
            dependsOn buildPackagesTask
            inputs.property("abis", abis)
            inputs.property("buildPython", python.buildPython).optional(true)
            inputs.property("pip", python.pip)
            inputs.property("pyc", python.pyc.pip).optional(true)
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
                if (!reqsArgs.isEmpty()) {
                    execBuildPython(python) {
                        args "-m", "chaquopy.pip_install"
                        args "--target", destinationDir
                        args("--android-abis", *abis)
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
                            // If the user passes --index-url, disable our repository as well
                            // as the default one.
                            args "--extra-index-url", "https://chaquo.com/pypi-7.0"
                        }
                        args "--implementation", Common.PYTHON_IMPLEMENTATION
                        args "--python-version", Common.PYTHON_VERSION
                        args "--abi", Common.PYTHON_ABI
                        args "--no-compile"
                        args python.pip.options
                    }
                    compilePyc(python, "pip", destinationDir)
                }

                // Requirements subdirectories must exist, or their ZIPs won't be created,
                // and the app will crash (#5631).
                for (subdirName in [Common.ABI_COMMON] + abis) {
                    def subdir = new File("$destinationDir/$subdirName")
                    if (!subdir.exists()) {
                        if (reqsArgs.isEmpty()) {
                            project.mkdir(subdir)
                        } else {
                            throw new GradleException("$subdir was not created: please " +
                                                      "check your buildPython setting")
                        }
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
            dependsOn buildPackagesTask
            inputs.property("buildPython", python.buildPython)
            inputs.property("pyc", python.pyc.src).optional(true)
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
                compilePyc(python, "src", mergeDir)
            }
        }
    }

    // We can't remove the .py files here because the static proxy generator needs them.
    // Instead, they'll be excluded when we call makeZip.
    void compilePyc(PythonExtension python, String tag, File dir) {
        Boolean setting = python.pyc[tag]
        if (setting == null || setting) {
            try {
                execBuildPython(python) {
                    args "-m", "chaquopy.pyc"
                    args "--quiet"  // TODO #5411: option to display syntax errors
                    if (!setting) {
                        args "--warning"
                    }
                    args dir
                }
            } catch (BuildPythonException e) {
                if (setting) {
                    throw e
                } else {
                    // Messages should be formatted the same as those from chaquopy.pyc.
                    println(
                        "Warning: Failed to compile to .pyc format: ${e.shortMessage}. See " +
                        "https://chaquo.com/chaquopy/doc/current/android.html#android-bytecode.")
                }
            }
        }
    }

    void createProxyTask(variant, PythonExtension python, Task reqsTask, Task mergeSrcTask) {
        File destinationDir = variantGenDir(variant, "proxies")
        Task proxyTask = project.task(taskName("generate", variant, "proxies")) {
            inputs.files(buildPackagesTask, reqsTask, mergeSrcTask)
            inputs.property("buildPython", python.buildPython).optional(true)
            inputs.property("staticProxy", python.staticProxy)
            outputs.dir(destinationDir)
            doLast {
                project.delete(destinationDir)
                project.mkdir(destinationDir)
                if (!python.staticProxy.isEmpty()) {
                    execBuildPython(python) {
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

    void execBuildPython(PythonExtension python, Closure closure) {
        if (python.buildPython == null) {
            throw new BuildPythonMissingException("Couldn't find Python")
        }

        ExecResult execResult = null
        try {
            execResult = project.exec {
                environment "PYTHONPATH", buildPackagesTask.buildPackagesZip
                commandLine python.buildPython
                args "-S"  // Avoid interference from site-packages. This is not inherited by
                           // subprocesses, so it's used again in pip_install.py.
                ignoreExitValue true  // A missing executable will still throw an exception.
                closure.delegate = delegate
                closure()
            }
        } catch (ExecException e) {
            throw new BuildPythonInvalidException(e.message)
        }
        if (python.buildPython[0].equals("py") && (execResult.exitValue == 103)) {
            // Before Python 3.6, stderr from the `py` command was lost
            // (https://bugs.python.org/issue25789). This is the only likely error.
            throw new BuildPythonMissingException(
                "$python.buildPython: couldn't find the requested version of Python")
        }

        try {
            execResult.assertNormalExitValue()
        } catch (ExecException e) {
            throw new BuildPythonFailedException(e.message)
        }
    }

    Task createTicketTask(variant) {
        def localProps = new Properties()
        project.rootProject.file('local.properties').withInputStream {
            localProps.load(it)
        }
        // null input properties give a warning in Gradle 4.4 (Android Studio 3.1). Luckily we're
        // no longer using the empty string to mean anything special.
        def key = localProps.getProperty("chaquopy.license", "")

        def applicationId
        if (isLibrary) {
            applicationId = localProps.getProperty("chaquopy.applicationId", "")
            if (applicationId.isEmpty() && !key.isEmpty()) {
                throw new GradleException(
                    "When building a library module with a license key, local.properties " +
                    "must contain a chaquopy.applicationId line identifying the app which " +
                    "the library will be built into.")
            }
        } else {
            applicationId = variant.applicationId
        }

        return assetTask(variant, "license") {
            inputs.property("app", applicationId)
            inputs.property("key", key)
            doLast {
                // No ticket is represented as an empty file rather than a missing one, so we
                // don't need to delete the extracted copy if the ticket is removed. To work
                // around https://github.com/Electron-Cash/Electron-Cash/issues/2136, we write
                // a single space rather than making it completely empty.
                def ticket = " ";

                if (key.length() > 0) {
                    final def TIMEOUT = 10000
                    def url = ("https://chaquo.com/license/get_ticket" +
                               "?app=$applicationId&key=$key")
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

    void createAssetsTasks(variant, python, Task reqsTask, Task mergeSrcTask,
                           Task ticketTask) {
        def excludePy = { FileTreeElement fte ->
            if (!fte.name.endsWith(".py")) {
                return false
            }
            return new File(fte.file.parent, fte.name + "c").exists()
        }

        def appAssetsTask = assetTask(variant, "app") {
            inputs.files(mergeSrcTask)
            doLast {
                makeZip(project.fileTree(mergeSrcTask.destinationDir)
                            .matching { exclude excludePy },
                        "$assetDir/${assetZip(Common.ASSET_APP)}")
            }
        }

        def reqsAssetsTask = assetTask(variant, "requirements") {
            inputs.files(reqsTask)
            doLast {
                for (subdir in reqsTask.destinationDir.listFiles()) {
                    makeZip(project.fileTree(subdir).matching { exclude excludePy },
                            "$assetDir/${assetZip(Common.ASSET_REQUIREMENTS, subdir.name)}")
                }
            }
        }

        def miscAssetsTask = assetTask(variant, "misc") {
            def runtimePython = getConfig("runtimePython")
            def runtimeModules = getConfig("runtimeModules", variant)
            def targetStdlib = getConfig("targetStdlib", variant)
            def targetNative = getConfig("targetNative", variant)
            inputs.files(runtimePython, runtimeModules, targetStdlib, targetNative)
            doLast {
                project.copy {
                    into assetDir
                    from(runtimePython) {
                        rename { assetZip(Common.ASSET_BOOTSTRAP) }
                    }
                    from(targetStdlib) {
                        rename { assetZip(Common.ASSET_STDLIB, Common.ABI_COMMON) }
                    }
                }

                // The following stdlib native modules are needed during bootstrap and are
                // pre-extracted; all others are loaded from a .zip using AssetFinder.
                def BOOTSTRAP_NATIVE_STDLIB = [
                    "_ctypes.so",  // java.primitive and importer
                    "_csv.so",  // importlib.metadata < importer
                    "_datetime.so",  // calendar < importer (see test_datetime)
                    "_hashlib.so",  // rsa < license.pxi (see test_hashlib)
                    "_json.so",  // check_ticket < license.pxi (see test_json)
                    "_random.so",  // tempfile < random < importer
                    "_struct.so",  // zipfile < importer
                    "binascii.so",  // zipfile < importer
                    "math.so",  // datetime < calendar < importer
                    "mmap.so",  // elftools < importer
                    "zlib.so",  // zipimport
                ]

                for (abi in getAbis(variant)) {
                    project.ant.unzip(src: getNativeArtifact(targetNative, abi),
                                      dest: assetDir) {
                        patternset() {
                            include(name: "lib-dynload/**")
                        }
                    }
                    makeZip(project.fileTree("$assetDir/lib-dynload/$abi")
                                .matching { exclude BOOTSTRAP_NATIVE_STDLIB },
                            "$assetDir/${assetZip(Common.ASSET_STDLIB, abi)}")

                    def bootstrapDir = "$assetDir/$Common.ASSET_BOOTSTRAP_NATIVE/$abi"
                    project.copy {
                        into bootstrapDir
                        from("$assetDir/lib-dynload/$abi") {
                            include BOOTSTRAP_NATIVE_STDLIB
                        }
                        runtimeModules.resolvedConfiguration.resolvedArtifacts.each { ra ->
                            if (ra.classifier == abi) {
                                from(ra.file) {
                                    into "java"
                                    rename { "${ra.name}.${ra.extension}" }
                                }
                            }
                        }
                    }
                    project.delete("$assetDir/lib-dynload")
                }
                extractResource(Common.ASSET_CACERT, assetDir)
            }
        }
        assetTask(variant, "build") {
            inputs.files(ticketTask, appAssetsTask, reqsAssetsTask, miscAssetsTask)
            doLast {
                def buildJson = new JSONObject()
                buildJson.put("assets", hashAssets(ticketTask, appAssetsTask, reqsAssetsTask,
                                                   miscAssetsTask))
                project.file("$assetDir/$Common.ASSET_BUILD_JSON").text = buildJson.toString(4)
            }
        }
    }

    // Based on org/gradle/api/internal/file/archive/ZipCopyAction.java. This isn't part of
    // the Gradle public API except via the Zip task, which we're not using because we'd need
    // to refactor to have one task per ZIP.
    //
    // The usual alternative is to use ant.zip, but that has other problems:
    //   * It only takes simple exclusion patterns, so there's no way to say "exclude .py
    //     files which have a corresponding .pyc".
    //   * It has no equivalent to preserveFileTimestamps, so we'd have to actually set the
    //     timestamps of all the input files.
    def makeZip(FileTree tree, Object outFile) {
        new ZipArchiveOutputStream(project.file(outFile)).withCloseable { zip ->
            // UTF-8 filename encoding is apparently on by default on Linux and off by default on
            // Windows: this alters the resulting ZIP file even if all filenames are ASCII.
            zip.setEncoding("UTF-8")

            // This is the same timestamp used by Gradle's preserveFileTimestamps setting.
            // The UTC timestamp generated here will vary according to the current timezone,
            // but the local time will be constant, and that's what gets stored in the ZIP.
            def timestamp = new GregorianCalendar(1980, Calendar.FEBRUARY, 1, 0, 0, 0)
                .getTimeInMillis()

            tree.visit(new ReproducibleFileVisitor() {
                boolean isReproducibleFileOrder() {
                    return true
                }
                void visitDir(FileVisitDetails details) {
                    def entry = new ZipArchiveEntry(details.path + "/")
                    entry.setTime(timestamp)
                    zip.putArchiveEntry(entry)
                    zip.closeArchiveEntry()
                }
                void visitFile(FileVisitDetails details) {
                    def entry = new ZipArchiveEntry(details.path)
                    entry.setTime(timestamp)
                    zip.putArchiveEntry(entry)
                    details.copyTo(zip)
                    zip.closeArchiveEntry()
                }
            })
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

        extendMergeTask(project.tasks.getByName(
            "${isLibrary ? "package" : "merge"}${variant.name.capitalize()}Assets"), t)
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
                // file.bytes may exhaust Java heap space, so read the file in smaller blocks.
                file.withInputStream {
                    def buf = new byte[1024 * 1024]
                    def len
                    while ((len = it.read(buf)) != -1) {
                        digest.update(buf, 0, len)
                    }
                }
                assetsJson.put(path, digest.digest().encodeHex())
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
                            fcd.relativePath = new RelativePath(
                                 !fcd.file.isDirectory(),
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

    File extractResource(String name, targetDir) {
        return extractResource(name, targetDir, new File(name).name)
    }

    File extractResource(String name, targetDir, String targetName) {
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
        return outFile
    }
}


class PythonExtension extends BaseExtension {
    Project project
    String[] buildPython
    Set<String> staticProxy = new TreeSet<>()
    PipExtension pip = new PipExtension()
    PycExtension pyc = new PycExtension()

    PythonExtension(Project project) {
        this.project = project
    }

    void setDefaults() {
        for (version in [Common.PYTHON_VERSION_SHORT, Common.PYTHON_VERSION_MAJOR]) {
            if (System.getProperty("os.name").startsWith("Windows")) {
                // See PEP 397. After running the official Windows installer with
                // default settings, this will be the only Python thing on the PATH.
                buildPython = ["py", "-$version"] as String[]
            } else {
                // See PEP 394.
                buildPython = ["python$version"] as String[]
            }
            if (checkBuildPython()) {
                break
            } else {
                buildPython = null
            }
        }
        pip.setDefaults()
        pyc.setDefaults()
    }

    boolean checkBuildPython() {
        try {
            project.exec {
                commandLine buildPython
                args "--version"
                standardOutput = new ByteArrayOutputStream()
                errorOutput = new ByteArrayOutputStream()
            }
            return true
        } catch (ExecException e) {
            return false
        }
    }

    void version(String v) {
        if (v.equals(Common.PYTHON_VERSION)) {
            println("Warning: Python 'version' setting is no longer required and should be " +
                    "removed from build.gradle.")
        } else {
            throw new GradleException(
                "This version of Chaquopy does not include Python version $v. " +
                "Either remove 'version' from build.gradle to use Python $Common.PYTHON_VERSION, " +
                "or see https://chaquo.com/chaquopy/doc/current/versions.html for other options.")
        }
    }

    void buildPython(String... bp) {
        buildPython = bp
        if (!checkBuildPython() && bp.length == 1) {
            // Backward compatibility for when buildPython only took a single string.
            buildPython = bp[0].split(/\s+/)
        }
    }

    void staticProxy(String... modules)         { staticProxy.addAll(modules) }
    void pip(Closure closure)                   { applyClosure(pip, closure) }
    void pyc(Closure closure)                   { applyClosure(pyc, closure) }

    void extractPackages(String... packages) {
        println("Warning: Python 'extractPackages' setting is no longer required and should " +
                "be removed from build.gradle.")
    }

    void mergeFrom(PythonExtension overlay) {
        buildPython = chooseNotNull(overlay.buildPython, this.buildPython)
        staticProxy.addAll(overlay.staticProxy)
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

    // Options are tracked separately from requirements because when installing the second and
    // subsequent ABIs, pip_install uses the same options with a different set of requirements.
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
    Boolean src
    Boolean pip
    Boolean stdlib

    void setDefaults() {
        src = null
        pip = null
        stdlib = true
    }

    void src(boolean value) { src = value }
    void pip(boolean value) { pip = value }
    void stdlib(boolean value) { stdlib = value }

    void mergeFrom(PycExtension overlay) {
        src = chooseNotNull(overlay.src, src)
        pip = chooseNotNull(overlay.pip, pip)
        stdlib = chooseNotNull(overlay.stdlib, stdlib)
    }
}


class BaseExtension implements Serializable {
    // If a setting's default value is not null or empty, we can't just set it in a field
    // initializer, because then a value explicitly set by the user in defaultConfig could be
    // overridden by a default value from a product flavor. Instead, such values are set in
    // this method, which is only called on defaultConfig.
    void setDefaults() {}

    static void applyClosure(BaseExtension be, Closure closure) {
        closure.delegate = be
        closure()
    }

    static <T> T chooseNotNull(T overlay, T base) {
        return overlay != null ? overlay : base
    }
}


class BuildPythonException extends GradleException {
    static final String ADVICE = (
        "set buildPython to your Python executable path. See " +
        "https://chaquo.com/chaquopy/doc/current/android.html#buildpython.")
    String shortMessage

    BuildPythonException(String shortMessage, String suffix) {
        super(shortMessage + suffix)
        this.shortMessage = shortMessage
    }
}

// Message will be something like "Couldn't find Python".
class BuildPythonMissingException extends BuildPythonException {
    BuildPythonMissingException(String message) {
        super(message, ". Please either install it, or " + ADVICE)
    }
}

// Message will be something like "Process 'command 'py'' finished with non-zero exit value 1",
// so we need to tell the user how to see the command output.
class BuildPythonFailedException extends BuildPythonException {
    BuildPythonFailedException(String message) {
        super(message,
              "\n\nTo view full details in Android Studio:\n" +
              "* In version 3.6 and newer, click the 'Build: failed' caption to the left " +
              "of this message.\n" +
              "* In version 3.5 and older, click the 'Toggle view' button to the left of " +
              "this message.\n" +
              "* Then scroll up to see the full output.")
    }
}

// Message will be something like "A problem occurred starting process 'command 'python''".
class BuildPythonInvalidException extends BuildPythonException {
    BuildPythonInvalidException(String message) {
        super(message, ". Please " + ADVICE)
    }
}
