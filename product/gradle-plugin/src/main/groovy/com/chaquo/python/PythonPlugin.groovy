package com.chaquo.python

import org.apache.commons.compress.archivers.zip.*
import org.gradle.api.*
import org.gradle.api.artifacts.Configuration
import org.gradle.api.file.*
import org.gradle.api.initialization.dsl.ScriptHandler
import org.gradle.api.plugins.*
import org.gradle.api.tasks.TaskInputs
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
    static final def MIN_ANDROID_PLUGIN_VER = VersionNumber.parse("4.2.0")

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

        // Load dependencies from the same buildscript context as the Chaquopy plugin itself,
        // so they'll come from the same repository.
        buildscript = findPlugin("com.chaquo.python", "gradle").project.buildscript

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

    static class PluginInfo {
        Project project
        VersionNumber version
    }

    PluginInfo findPlugin(String group, String name) {
        Project p = project
        while (p != null) {
            for (art in p.buildscript.configurations.getByName("classpath")
                        .resolvedConfiguration.resolvedArtifacts) {
                def dep = art.moduleVersion.id
                if (dep.group == group  &&  dep.name == name) {
                    return new PluginInfo(project: p,
                                          version: VersionNumber.parse(dep.version))
                }
            }
            p = p.parent
        }
        return null;
    }

    VersionNumber getAndroidPluginVersion() {
        final def ADVICE =
            "please edit the version of com.android.application, com.android.library or " +
            "com.android.tools.build:gradle in your top-level build.gradle file. See " +
            "https://chaquo.com/chaquopy/doc/current/versions.html."

        def info = findPlugin("com.android.tools.build", "gradle")
        if (info == null) {
            // This wording is checked by AndroidPlugin.test_old.
            println("Warning: Chaquopy was unable to determine the Android Gradle plugin " +
                    "version. The minimum supported version is $MIN_ANDROID_PLUGIN_VER. " +
                    "If you experience problems, " + ADVICE)
            return null
        }
        if (info.version < MIN_ANDROID_PLUGIN_VER) {
            throw new GradleException(
                "This version of Chaquopy requires Android Gradle plugin " +
                "version $MIN_ANDROID_PLUGIN_VER or later: " + ADVICE)
        }
        return info.version
    }

    PythonExtension extendProductFlavor(ExtensionAware ea) {
        def python = new PythonExtension(project)
        ea.extensions.add(NAME, python)
        return python
    }

    // TODO #5341: support setRoot
    void extendSourceSets() {
        android.sourceSets.all { sourceSet ->
            Object[] args = null
            def javaSet = sourceSet.java
            if (androidPluginVer < VersionNumber.parse("7.2.0-alpha01")) {
                args = [sourceSet.name + " Python source", project, javaSet.type]
            } else {
                args = [sourceSet.name, "Python source", project, javaSet.type]
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
            def python = new PythonExtension(project)
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
            createAssetsTasks(variant, python, reqsTask, mergeSrcTask)
            createJniLibsTasks(variant, python)
        }
    }

    void createConfigs(variant, PythonExtension python) {
        buildscript.dependencies {
            add(getConfig("runtimePython").name,
                runtimeDep(assetZip(Common.ASSET_BOOTSTRAP), python.version))
            add(getConfig("targetStdlib", variant).name,
                targetDep(python, python.pyc.stdlib ? "stdlib-pyc" : "stdlib"))
        }

        for (abi in getAbis(variant)) {
            if (! Common.ABIS.contains(abi)) {
                throw new GradleException("$variant.name: Chaquopy does not support the ABI " +
                                          "'$abi'. Supported ABIs are ${Common.ABIS}.")
            }
            buildscript.dependencies {
                add(getConfig("runtimeJni", variant).name,
                    runtimeDep("libchaquopy_java.so", python.version, abi))
                add(getConfig("runtimeModules", variant).name,
                    runtimeDep("chaquopy.so", python.version, abi))
                add(getConfig("targetNative", variant).name,
                    targetDep(python, abi))
            }
        }
    }

    Configuration getConfig(String name, variant=null) {
        def variantName = (variant != null) ? variant.name : ""
        def configName = "$NAME${variantName.capitalize()}${name.capitalize()}"
        return buildscript.configurations.maybeCreate(configName)
    }

    Object targetDep(PythonExtension python, String classifier) {
        def entry = pythonVersionInfo(python.version)
        return "com.chaquo.python:target:$entry.key-$entry.value:$classifier@zip"
    }

    Map.Entry<String, String> pythonVersionInfo(String version) {
        for (entry in Common.PYTHON_VERSIONS.entrySet()) {
            if (entry.key.startsWith(version)) {
                return entry
            }
        }
        // Since the version has already been validated by PythonExtension.version, this
        // should be impossible.
        throw new GradleException("Failed to find information for Python version " +
                                  "'$version'.")
    }

    Object runtimeDep(String filename, String pyVersion=null, String abi=null) {
        def dotPos = filename.lastIndexOf(".")
        def result = [
            group: "com.chaquo.python.runtime",
            name: filename.substring(0, dotPos),
            version: PLUGIN_VERSION,
            ext: filename.substring(dotPos + 1),
        ]
        def classifiers = [pyVersion, abi].findAll { it != null }
        if (!classifiers.isEmpty()) {
            result.put("classifier", classifiers.join("-"))
        }
        return result
    }

    File getNativeArtifact(Configuration config, String pyVersion, String abi) {
        return config.resolvedConfiguration.resolvedArtifacts.find {
            it.classifier == [pyVersion, abi].findAll { it != null }.join("-")
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
        return project.task("extractPythonBuildPackages") {
            // To avoid the the Windows 260-character limit, make the path as short as
            // possible.
            ext.pythonPath = "$genDir/bp"
            outputs.files(project.fileTree(pythonPath) {
                exclude "**/__pycache__"
            })
            doLast {
                project.delete(pythonPath)
                project.mkdir(pythonPath)
                def zipPath = extractResource("gradle/build-packages.zip", genDir)
                project.copy {
                    from project.zipTree(zipPath)
                    into pythonPath
                }
                project.delete(zipPath)
                project.delete("$genDir/bp.zip")  // From Chaquopy 13.0 and older.
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
            inputs.property("minApiLevel", variant.mergedFlavor.minSdkVersion.apiLevel)
            inputs.property("buildPython", python.buildPython).optional(true)
            inputs.property("pip", python.pip)
            inputs.property("pyc", python.pyc.pip).optional(true)

            def reqsArgs = []
            for (req in python.pip.reqs) {
                reqsArgs.addAll(["--req", req])
                addReqInput(inputs, req, project.projectDir)
            }
            for (reqFile in python.pip.reqFiles) {
                reqsArgs.addAll(["--req-file", reqFile])
                inputs.files(reqFile)
                try {
                    def file = project.file(reqFile)
                    file.eachLine {
                        // Pip resolves `-r` and `-c` lines  (which we don't currently
                        // detect) relative to the location of the containing requirements
                        // file, while paths to actual requirements are resolved relative
                        // to the working directory
                        // (https://github.com/pypa/pip/pull/4208#issuecomment-429120743).
                        addReqInput(inputs, it, project.projectDir)
                    }
                } catch (FileNotFoundException e) {}
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
                        args("--min-api-level", inputs.properties["minApiLevel"])
                        args reqsArgs
                        args "--"
                        args "--disable-pip-version-check"
                        if (!("--index-url" in python.pip.options ||
                              "-i" in python.pip.options)) {
                            // If the user passes --index-url, disable our repository as well
                            // as the default one.
                            args "--extra-index-url", "https://chaquo.com/pypi-7.0"
                            args "--extra-index-url", "https://chaquo.com/pypi-13.1"
                            }
                        args "--implementation", Common.PYTHON_IMPLEMENTATION
                        args "--python-version", pythonVersionInfo(python.version).key
                        args "--abi", (Common.PYTHON_IMPLEMENTATION +
                                       python.version.replace(".", ""))
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

    // This does not currently detect changes to indirect requirements or constraints
    // files (#719).
    void addReqInput(TaskInputs inputs, String req, File baseDir) {
        // # is used for comments, and ; for environment markers.
        req = req.replaceAll(/[#;].*/, "").trim()
        if (req.isEmpty()) return

        File file
        try {
            file = new File(req)
            if (! file.isAbsolute()) {
                // Passing two absolute paths to the File constructor will simply
                // concatenate them rather than returning the second one.
                file = new File(baseDir, req)
            }
            if (! file.exists()) {
                file = null
            }
        } catch (Exception e) {
            // In case any of the above code throws on an invalid filename.
            file = null
        }
        // Do this outside of the try block to avoid hiding exceptions.
        if (file != null) {
            if (file.isDirectory()) {
                inputs.files(project.fileTree(file) {
                    // Ignore any files which may be written while installing.
                    exclude "build", "dist", "**/*.dist-info", "**/*.egg-info"
                    exclude "**/__pycache__"  // See test_pep517_backend_path
                })
            } else {
                inputs.files(file)
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
            inputs.property("buildPython", python.buildPython).optional(true)
            inputs.property("pyc", python.pyc.src).optional(true)
            inputs.files(dirSets.collect { it.sourceFiles })
            outputs.dir(destinationDir)
            doLast {
                project.delete(mergeDir)
                project.mkdir(mergeDir)
                project.copy {
                    into mergeDir
                    exclude "**/*.pyc", "**/*.pyo"
                    exclude "**/*.egg-info"  // See ExtractPackages.test_change.
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
                    args "--python", python.version
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
                environment "PYTHONPATH", buildPackagesTask.pythonPath
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
        try {
            execResult.assertNormalExitValue()
        } catch (ExecException e) {
            throw new BuildPythonFailedException(e.message)
        }
    }

    void createAssetsTasks(variant, PythonExtension python, Task reqsTask,
                           Task mergeSrcTask) {
        def excludePy = { FileTreeElement fte ->
            if (fte.name.endsWith(".py") &&
                new File(fte.file.parent, fte.name + "c").exists()) {
                def dottedPath = fte.path.replace("/", ".")
                return ! python.extractPackages.any { dottedPath.startsWith(it + ".") }
            } else {
                return false
            }
        }

        def appAssetsTask = assetTask(variant, "app") {
            inputs.files(mergeSrcTask)
            inputs.property("extractPackages", python.extractPackages)
            doLast {
                makeZip(project.fileTree(mergeSrcTask.destinationDir)
                            .matching { exclude excludePy },
                        "$assetDir/${assetZip(Common.ASSET_APP)}")
            }
        }

        def reqsAssetsTask = assetTask(variant, "requirements") {
            inputs.files(reqsTask)
            inputs.property("extractPackages", python.extractPackages)
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
                // pre-extracted by AndroidPlatform so they can be loaded with the
                // standard FileFinder. All other native modules are loaded from a .zip using
                // AssetFinder.
                def BOOTSTRAP_NATIVE_STDLIB = [
                    "_ctypes.so",  // java.primitive and importer
                    "_datetime.so",  // calendar < importer (see test_datetime)
                    "_random.so",  // random < tempfile < zipimport
                    "_sha512.so",  // random < tempfile < zipimport
                    "_struct.so",  // zipfile < importer
                    "binascii.so",  // zipfile < importer
                    "math.so",  // datetime < calendar < importer
                    "mmap.so",  // elftools < importer
                    "zlib.so",  // zipimport
                ]

                for (abi in getAbis(variant)) {
                    project.ant.unzip(
                        src: getNativeArtifact(targetNative, null, abi),
                        dest: assetDir
                    ) {
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
                            if (ra.classifier == "$python.version-$abi") {
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
            inputs.files(appAssetsTask, reqsAssetsTask, miscAssetsTask)
            doLast {
                def buildJson = new JSONObject()
                buildJson.put("python_version", python.version)
                buildJson.put("assets", hashAssets(appAssetsTask, reqsAssetsTask,
                                                   miscAssetsTask))
                buildJson.put("extract_packages", new JSONArray(python.extractPackages))
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
                        from getNativeArtifact(runtimeJni, python.version, abi)
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
    String version
    String[] buildPython
    Set<String> staticProxy = new TreeSet<>()
    Set<String> extractPackages = new TreeSet<>()
    PipExtension pip = new PipExtension()
    PycExtension pyc = new PycExtension()

    PythonExtension(Project project) {
        this.project = project
    }

    void setDefaults() {
        version = Common.DEFAULT_PYTHON_VERSION
        pip.setDefaults()
        pyc.setDefaults()
    }

    void version(String v) {
        if (v in Common.PYTHON_VERSIONS_SHORT) {
            version = v
            if (v != Common.DEFAULT_PYTHON_VERSION) {
                println("Warning: Python version $v may have fewer packages available. " +
                        "If you experience problems, try switching to version " +
                        "${Common.DEFAULT_PYTHON_VERSION}.")
            }
        } else {
            throw new GradleException("Invalid Python version '$v'. Available versions " +
                                      "are ${Common.PYTHON_VERSIONS_SHORT}.")
        }
    }

    boolean checkBuildPython(bp) {
        try {
            project.exec {
                commandLine bp
                args "--version"
                standardOutput = new ByteArrayOutputStream()
                errorOutput = new ByteArrayOutputStream()
            }
            return true
        } catch (ExecException e) {
            return false
        }
    }

    void buildPython(String... bp) {
        buildPython = bp
        if (!checkBuildPython(bp) && bp.length == 1) {
            // Backward compatibility for when buildPython only took a single string.
            buildPython = bp[0].split(/\s+/)
        }
    }

    String[] getBuildPython() {
        if (buildPython == null) {
            List<List<String>> bps = new ArrayList<>()
            for (suffix in [version, version.split(/\./)[0]]) {
                if (System.getProperty("os.name").startsWith("Windows")) {
                    // See PEP 397. After running the official Windows installer with
                    // default settings, this will be the only Python thing on the PATH.
                    bps.add(["py", "-$suffix"])
                } else {
                    // See PEP 394.
                    bps.add(["python$suffix"])
                }
            }

            // On Windows, both venv and conda create environments containing only a
            // `python` executable, not `python3`, `python3.x`, or `py`. It's also
            // reasonable to use this as a final fallback on Unix (#752).
            bps.add(["python"])

            for (bp in bps) {
                if (checkBuildPython(bp)) {
                    buildPython = bp as String[]
                    break
                }
            }
        }
        return buildPython
    }

    void staticProxy(String... modules)         { staticProxy.addAll(modules) }
    void extractPackages(String... packages)    { extractPackages.addAll(packages) }
    void pip(Closure closure)                   { applyClosure(pip, closure) }
    void pyc(Closure closure)                   { applyClosure(pyc, closure) }

    void mergeFrom(PythonExtension overlay) {
        version = chooseNotNull(overlay.version, this.version)
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
              "* Click the 'Build: failed' caption to the left of this message.\n" +
              "* Then scroll up to see the full output.")
    }
}

// Message will be something like "A problem occurred starting process 'command 'python''".
class BuildPythonInvalidException extends BuildPythonException {
    BuildPythonInvalidException(String message) {
        super(message, ". Please " + ADVICE)
    }
}
