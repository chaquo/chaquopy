package com.chaquo.python

import com.android.build.api.variant.*
import com.chaquo.python.internal.*
import com.chaquo.python.internal.Common.assetZip
import com.chaquo.python.internal.Common.osName
import org.apache.commons.compress.archivers.zip.*
import org.gradle.api.*
import org.gradle.api.artifacts.*
import org.gradle.api.file.*
import org.gradle.api.provider.Provider
import org.gradle.api.tasks.*
import org.gradle.kotlin.dsl.*
import org.gradle.process.internal.*
import org.json.*
import java.io.*
import java.security.*
import java.util.*
import kotlin.reflect.*


internal class TaskBuilder(
    val plugin: PythonPlugin, val variant: Variant, val python: PythonExtension,
    val abis: List<String>
) {
    val project = plugin.project
    lateinit var buildPackagesTask: Provider<BuildPackagesTask>
    lateinit var srcTask: Provider<OutputDirTask>
    lateinit var reqsTask: Provider<OutputDirTask>

    fun build() {
        createConfigs()
        buildPackagesTask = createBuildPackagesTask()
        srcTask = createSrcTask()
        reqsTask = createReqsTask()
        createProxyTask()
        createAssetsTasks()
        createJniLibsTasks()
    }

    fun createConfigs() {
        plugin.addRuntimeDependency(
            "bootstrap", assetZip(Common.ASSET_BOOTSTRAP), variant, python)
        plugin.addTargetDependency(
            "stdlib", variant, python,
            if (python.pyc.stdlib == false) "stdlib" else "stdlib-pyc")

        for (abi in abis) {
            plugin.addRuntimeDependency(
                "jni", "libchaquopy_java.so", variant, python, abi)
            plugin.addRuntimeDependency(
                "modules", "chaquopy.so", variant, python, abi)
            plugin.addTargetDependency("native", variant, python, abi)
        }
    }

    fun createBuildPackagesTask() =
        registerTask("extract", "buildPackages", BuildPackagesTask::class) {
            var bpInfo: BuildPythonInfo?
            try {
                bpInfo = findBuildPython()
                inputs.property("info", bpInfo.info)
            } catch (e: BuildPythonException) {
                bpInfo = null
                exception = e
            }

            // Keep the path short to avoid the the Windows 260-character limit.
            outputDir.set(plugin.buildSubdir("env", variant))

            if (bpInfo != null) {
                doLast {
                    plugin.execOps.exec {
                        commandLine(bpInfo.commandLine)
                        args("-m", "venv", "--without-pip", project.file(outputDir))
                    }

                    val zipPath = plugin.extractResource(
                        "gradle/build-packages.zip", plugin.buildSubdir())
                    project.copy {
                        from(project.zipTree(zipPath))
                        into(sitePackages)
                    }
                    project.delete(zipPath)

                    // Pre-generate the __pycache__ directories to avoid the outputDir
                    // contents changing and breaking the up to date checks.
                    plugin.execOps.exec {
                        commandLine(bpInfo.commandLine)
                        args("-Wignore", "-m", "compileall", "-qq",
                             project.file(outputDir))
                    }
                }
            }
        }

    abstract class BuildPackagesTask : OutputDirTask() {
        @get:Internal
        lateinit var exception: Exception

        @get:Internal
        val pythonExecutable by lazy {
            if (::exception.isInitialized) {
                throw exception
            } else {
                project.file(outputDir).resolve(
                    if (osName() == "windows") "Scripts/python.exe" else "bin/python"
                )
            }
        }

        @get:Internal
        val sitePackages by lazy {
            val libPythonDir = if (osName() == "windows") {
                assertExists(project.file(outputDir).resolve("Lib"))
            } else {
                val libDir = assertExists(project.file(outputDir).resolve("lib"))
                val pythonDirs = libDir.listFiles()!!.filter {
                    it.name.startsWith("python")
                }
                if (pythonDirs.size != 1) {
                    throw GradleException(
                        "found ${pythonDirs.size} python directories in $libDir")
                }
                pythonDirs[0]
            }
            libPythonDir.resolve("site-packages")
        }
    }

    fun createSrcTask() =
        registerTask("merge", "sources") {
            inputs.files(buildPackagesTask)
            inputs.property("pyc", python.pyc.src).optional(true)

            val dirSets = ArrayList<SourceDirectorySet>()
            for (name in sourceSetNames()) {
                val dirSet = plugin.extension.sourceSets.findByName(name)
                if (dirSet != null) {
                    dirSets += dirSet
                    inputs.files(dirSet)
                }
            }

            outputDir.set(plugin.buildSubdir("sources", variant))
            doLast {
                project.copy {
                    for (dirSet in dirSets) {
                        for (srcDir in dirSet.srcDirs) {
                            from(srcDir) {
                                exclude(dirSet.excludes)
                                include(dirSet.includes)
                            }
                        }
                    }
                    duplicatesStrategy = DuplicatesStrategy.FAIL  // Overridden below

                    exclude("**/*.pyc", "**/*.pyo")
                    exclude("**/*.egg-info")  // See ExtractPackages.test_change
                    into(outputDir)

                    // Allow duplicates for empty files (e.g. __init__.py)
                    eachFile {
                        if (file.length() == 0L) {
                            val destFile = project.file(outputDir).resolve(path)
                            if (destFile.exists() && destFile.length() == 0L) {
                                duplicatesStrategy = DuplicatesStrategy.INCLUDE
                            }
                        }
                    }
                }
                compilePyc(python.pyc.src, project.file(outputDir))
            }
        }

    fun sourceSetNames() = sequence {
        val buildType = variant.buildType!!
        yield("main")
        yield(buildType)

        for ((_, flavor) in variant.productFlavors) {
            yield(flavor)
            yield(flavor + buildType.capitalize())
        }

        if (variant.productFlavors.size >= 2) {
            val flavorName = variant.flavorName  // All flavors combined
            if (flavorName != null) {
                yield(flavorName)
                yield(flavorName + buildType.capitalize())
            }
        }
    }

    fun createReqsTask() =
        registerTask("install", "requirements") {
            inputs.files(buildPackagesTask)
            inputs.property("pyc", python.pyc.pip).optional(true)

            // Keep the path short to avoid the the Windows 260-character limit.
            outputDir.set(plugin.buildSubdir("pip", variant))

            val reqsArgs = ArrayList<String>()
            for (req in python.pip.reqs) {
                reqsArgs += listOf("--req", req)
                addReqInput(inputs, req, project.projectDir)
            }
            for (reqFile in python.pip.reqFiles) {
                reqsArgs += listOf("--req-file", reqFile)
                inputs.files(reqFile)
                try {
                    project.file(reqFile).forEachLine { line ->
                        // # is used for comments, and ; for environment markers.
                        val req = line.replace(Regex("[#;].*"), "").trim { it <= ' ' }
                        if (! req.isEmpty()) {
                            addReqInput(inputs, req, project.projectDir)
                        }
                    }
                } catch (_: FileNotFoundException) {}
            }

            val args = ArrayList<String>().apply {
                args("-m", "chaquopy.pip_install")
                args("--target", project.file(outputDir))
                args("--android-abis", *abis.toTypedArray())
                args("--min-api-level", variant.minSdkVersion.apiLevel)
                args(reqsArgs)
                args("--")
                args("--disable-pip-version-check")

                // If the user passes  a custom index url, disable our repository as
                // well as the default one.
                if (!listOf("--index-url", "-i").any {
                        it in python.pip.options
                    }) {
                    args("--extra-index-url", "https://chaquo.com/pypi-13.1")
                }

                // Pass the full Python version, but without any pre-release segment.
                args("--implementation", Common.PYTHON_IMPLEMENTATION)
                args("--python-version",
                     """\d+\.\d+\.\d+""".toRegex()
                         .find(pythonVersionInfo(python).key)!!.value)
                args("--abi",
                     Common.PYTHON_IMPLEMENTATION + python.version!!.replace(".", ""))

                args("--no-compile")
                args(python.pip.options)
            }
            inputs.property("args", args)

            doLast {
                if (!reqsArgs.isEmpty()) {
                    execBuildPython(args)
                    compilePyc(python.pyc.pip, project.file(outputDir))
                }

                // In #250 it looks like someone used a buildPython which returned
                // success without doing anything. This led to a runtime crash because
                // the requirements ZIPs were missing from the app.
                for (subdirName in listOf(Common.ABI_COMMON) + abis) {
                    val subdir = project.file(outputDir).resolve(subdirName)
                    if (!subdir.exists()) {
                        if (reqsArgs.isEmpty()) {
                            project.mkdir(subdir)
                        } else {
                            throw GradleException("$subdir was not created: please " +
                                                  "check your buildPython setting")
                        }
                    }
                }
            }
        }

    // TODO #719: Detect changes to indirect requirements or constraints files. The
    // `baseDir` argument will be useful for that, because pip resolves `-r` and `-c`
    // lines relative to the location of the containing requirements file, while paths
    // to actual requirements are resolved relative to the working directory
    // (https://github.com/pypa/pip/pull/4208#issuecomment-429120743).
    fun addReqInput(inputs: TaskInputs, req: String, baseDir: File) {
        var file: File?
        try {
            file = File(req)
            if (! file.isAbsolute) {
                // Passing two absolute paths to the File constructor will simply
                // concatenate them rather than returning the second one.
                file = File(baseDir, req)
            }
            if (! file.exists()) {
                file = null
            }
        } catch (_: Exception) {
            // In case any of the above code throws on an invalid filename.
            file = null
        }

        // Do this outside of the try block to avoid hiding exceptions.
        if (file != null) {
            if (file.isDirectory) {
                inputs.files(project.fileTree(file) {
                    // Ignore any files which may be written while installing.
                    exclude("build", "dist", "**/*.dist-info", "**/*.egg-info")
                    exclude("**/__pycache__") // See test_pep517_backend_path
                })
            } else {
                inputs.files(file)
            }
        }
    }

    fun createProxyTask() {
        registerGenerateTask(variant.sources.java!!, "proxies") {
            inputs.files(buildPackagesTask, reqsTask, srcTask)
            outputDir.set(plugin.buildSubdir("proxies", variant))

            val args = ArrayList<String>().apply {
                args("-m", "chaquopy.static_proxy")
                args("--path",
                     listOf(
                         project.file(srcTask.get().outputDir),
                         project.file(reqsTask.get().outputDir).resolve("common")
                     ).joinToString(File.pathSeparator))
                args("--java", project.file(outputDir))
                args(python.staticProxy)
            }
            inputs.property("args", args)

            doLast {
                if (!python.staticProxy.isEmpty()) {
                    execBuildPython(args)
                }
            }
        }
    }

    fun createAssetsTasks() {
        // Exclude .py files which have a corresponding .pyc, unless unless they’re
        // included in extractPackages.
        val excludePy = { fte: FileTreeElement ->
            if (fte.name.endsWith(".py") &&
                File(fte.file.parent, fte.name + "c").exists()
            ) {
                ! python.extractPackages.any {
                    fte.path.replace("/", ".").startsWith(it + ".")
                }
            } else false
        }

        val srcAssetsTask = registerAssetTask("source") {
            inputs.files(srcTask)
            inputs.property("extractPackages", python.extractPackages)
            doLast {
                makeZip(project.fileTree(srcTask.get().outputDir)
                            .matching { exclude(excludePy) },
                        File(assetDir, assetZip(Common.ASSET_APP)))
            }
        }

        val reqsAssetsTask = registerAssetTask("requirements") {
            inputs.files(reqsTask)
            inputs.property("extractPackages", python.extractPackages)
            doLast {
                for (subdir in project.file(reqsTask.get().outputDir).listFiles()!!) {
                    makeZip(
                        project.fileTree(subdir).matching { exclude(excludePy) },
                        File(assetDir, assetZip(Common.ASSET_REQUIREMENTS, subdir.name)))
                }
            }
        }

        val miscAssetsTask = registerAssetTask("misc") {
            val runtimeBootstrap = plugin.getConfig("runtimeBootstrap", variant)
            val runtimeModules = plugin.getConfig("runtimeModules", variant)
            val targetStdlib = plugin.getConfig("targetStdlib", variant)
            val targetNative = plugin.getConfig("targetNative", variant)
            inputs.files(runtimeBootstrap, runtimeModules, targetStdlib, targetNative)

            doLast {
                project.copy {
                    fromRuntimeArtifact(runtimeBootstrap)
                    from(targetStdlib) {
                        rename { assetZip(Common.ASSET_STDLIB, Common.ABI_COMMON) }
                    }
                    into(assetDir)
                }

                // The following stdlib native modules are needed during bootstrap and are
                // pre-extracted by AndroidPlatform so they can be loaded with the
                // standard FileFinder. All other native modules are loaded from a .zip using
                // AssetFinder.
                //
                // If this list changes, search for references to this variable name to
                // find the tests that need to be updated.
                val BOOTSTRAP_NATIVE_STDLIB = mutableListOf(
                    "_bz2.*",  // zipfile < importer
                    "_ctypes.*",  // java.primitive and importer
                    "_datetime.*",  // calendar < importer (see test_datetime)
                    "_lzma.*",  // zipfile < importer
                    "_random.*",  // random < tempfile < zipimport
                    "_sha512.*",  // random < tempfile < zipimport
                    "_struct.*",  // zipfile < importer
                    "binascii.*",  // zipfile < importer
                    "math.*",  // datetime < calendar < importer
                    "mmap.*",  // elftools < importer
                    "zlib.*"  // zipimport
                )

                val versionParts = python.version!!.split(".")
                val versionInt =
                    (versionParts[0].toInt() * 100) + versionParts[1].toInt()
                if (versionInt >= 312) {
                    BOOTSTRAP_NATIVE_STDLIB.removeAll(listOf("_sha512.*"))
                    BOOTSTRAP_NATIVE_STDLIB.addAll(listOf(
                        "_sha2.*"  // random < tempfile < zipimport
                    ))
                }
                if (versionInt >= 313) {
                    BOOTSTRAP_NATIVE_STDLIB.removeAll(listOf("_sha2.*"))
                    BOOTSTRAP_NATIVE_STDLIB.addAll(listOf(
                        "_opcode.*"  // opcode < dis < inspect < importer
                    ))
                }

                for (abi in abis) {
                    project.copy {
                        from(project.zipTree(resolveArtifact(targetNative, abi).file))
                        include("lib-dynload/**")
                        into(assetDir)
                    }
                    makeZip(project.fileTree("$assetDir/lib-dynload/$abi")
                                .matching { exclude(BOOTSTRAP_NATIVE_STDLIB) },
                            File(assetDir, assetZip(Common.ASSET_STDLIB, abi)))

                    val bootstrapDir = "$assetDir/${Common.ASSET_BOOTSTRAP_NATIVE}/$abi"
                    project.copy {
                        from("$assetDir/lib-dynload/$abi")
                        include(BOOTSTRAP_NATIVE_STDLIB)
                        into(bootstrapDir)
                    }
                    project.delete("$assetDir/lib-dynload")

                    project.copy {
                        fromRuntimeArtifact(runtimeModules, abi)
                        into("$bootstrapDir/java")
                    }
                }
                plugin.extractResource(Common.ASSET_CACERT, assetDir)
            }
        }

        registerAssetTask("build") {
            val tasks = arrayOf(srcAssetsTask, reqsAssetsTask, miscAssetsTask)
            inputs.files(*tasks)
            doLast {
                val buildJson = JSONObject()
                buildJson.put("python_version", python.version)
                buildJson.put("assets", hashAssets(*tasks))
                buildJson.put("extract_packages", JSONArray(python.extractPackages))
                File(assetDir, Common.ASSET_BUILD_JSON).writeText(buildJson.toString(4))
            }
        }

    }

    fun registerAssetTask(
        name: String, configure: AssetDirTask.() -> Unit
    ) = registerGenerateTask(
        variant.sources.assets!!, "${name}Assets", AssetDirTask::class
    ) {
        outputDir.set(plugin.buildSubdir("assets/$name", variant))
        configure()
    }

    fun createJniLibsTasks() {
        registerGenerateTask(variant.sources.jniLibs!!, "jniLibs") {
            val runtimeJni = plugin.getConfig("runtimeJni", variant)
            val targetNative = plugin.getConfig("targetNative", variant)
            inputs.files(runtimeJni, targetNative)

            outputDir.set(plugin.buildSubdir("jniLibs", variant))
            doLast {
                val artifacts = targetNative.resolvedConfiguration.resolvedArtifacts
                for (art in artifacts) {
                    // Copy jniLibs/<arch>/ in the ZIP to jniLibs/<variant>/<arch>/ in
                    // the build directory.
                    // (https://discuss.gradle.org/t/copyspec-support-for-moving-files-directories/7412/1)
                    project.copy {
                        from(project.zipTree(art.file))
                        include("jniLibs/**")
                        into(outputDir)
                        eachFile {
                            relativePath = RelativePath(
                                !file.isDirectory(),
                                *relativePath.segments.let {
                                    it.sliceArray(1 until it.size)
                                })
                        }
                        includeEmptyDirs = false
                    }
                }

                for (abi in abis) {
                    project.copy {
                        fromRuntimeArtifact(runtimeJni, abi)
                        into(project.file(outputDir).resolve(abi))
                    }
                }
            }
        }
    }

    fun registerGenerateTask(
        sourceDirs: SourceDirectories, noun: String, configure: OutputDirTask.() -> Unit
    ) = registerGenerateTask(sourceDirs, noun, OutputDirTask::class, configure)

    fun <T: OutputDirTask> registerGenerateTask(
        sourceDirs: SourceDirectories,
        noun: String,
        cls: KClass<T>,
        configure: T.() -> Unit
    ): TaskProvider<T> {
        // addGeneratedSourceDirectory sets outputDir to a subdirectory of
        // build/generated. Run our own configure action afterwards so we can override
        // that to a shorter path inside build/python, and reduce the risk of hitting
        // the Windows 260 character limit.
        val task = registerTask("generate", noun, cls) {}
        sourceDirs.addGeneratedSourceDirectory(task, OutputDirTask::outputDir)
        task.configure(configure)
        return task
    }

    // We can't remove the .py files here because the static proxy generator needs them.
    // Instead, they'll be excluded when we call makeZip.
    fun compilePyc(setting: Boolean?, dir: File) {
        if (setting != false) {
            try {
                execBuildPython(ArrayList<String>().apply {
                    args("-m", "chaquopy.pyc")
                    args("--python", python.version!!)
                    args("--quiet")
                    if (setting != true) {
                        args("--warning")
                    }
                    args(dir)
                })
            } catch (e: BuildPythonException) {
                if (setting == true) {
                    throw e
                } else {
                    // Messages should be formatted the same as those from chaquopy.pyc.
                    warn("Failed to compile to .pyc format: ${e.shortMessage} See " +
                        "https://chaquo.com/chaquopy/doc/current/android.html#android-bytecode")
                }
            }
        }
    }

    fun warn(message: String) {
        // This prefix causes Android Studio to show the line as a warning in tree view.
        println("Warning: $message")
    }

    fun registerTask(
        verb: String, noun: String, configure: OutputDirTask.() -> Unit
    ) = registerTask(verb, noun, OutputDirTask::class, configure)

    fun <T: OutputDirTask> registerTask(
        verb: String, noun: String, cls: KClass<T>, configure: T.() -> Unit
    ): TaskProvider<T> {
        // This matches the format of the AGP's own task names.
        return project.tasks.register(
            "$verb${variant.name.capitalize()}Python${noun.capitalize()}",
            cls, configure)
    }

    fun resolveArtifact(config: Configuration, classifier: String): ResolvedArtifact {
        return config.resolvedConfiguration.resolvedArtifacts.find {
            it.classifier == classifier
        }!!
    }

    fun CopySpec.fromRuntimeArtifact(
        config: Configuration, abi: String? = null
    ) {
        val art = resolveArtifact(config, runtimeClassifier(python, abi))
        from(art.file) {
            rename { "${art.name}.${art.extension}" }
        }
    }

    fun execBuildPython(args: List<String>) {
        try {
            plugin.execOps.exec {
                executable(buildPackagesTask.get().pythonExecutable)
                this.args(args)
            }
        } catch (e: ExecException) {
            // Message will be something like "Process 'command 'py'' finished with
            // non-zero exit value 1", so we need to tell the user how to see the
            // command output.
            throw BuildPythonException(
                e.message!!,
                "\n\nTo view full details in Android Studio:\n" +
                "* Click the 'Build: failed' caption to the left of this message.\n" +
                "* Then scroll up to see the full output.")
        }
    }

    data class BuildPythonInfo(val commandLine: List<String>, val info: String)

    fun findBuildPython(): BuildPythonInfo {
        val version = python.version!!
        val bpSetting = python.buildPython

        val bps = sequence {
            if (bpSetting != null) {
                yield(bpSetting)

                // For convenience, buildPython may also be set to a single
                // space-separated string. If the user needs spaces within arguments,
                // then they'll have to use the multi-string form.
                if (bpSetting.size == 1 && bpSetting[0].contains(' ')) {
                    yield(bpSetting[0].split(Regex("""\s+""")))
                }
            } else {
                // Trying the `python3` and `py -3` commands is usually unnecessary, but
                // might be useful in some situations.
                for (suffix in listOf(version, version.split(".")[0])) {
                    if (osName() == "windows") {
                        yield(listOf("py", "-$suffix"))
                    } else {
                        yield(listOf("python$suffix"))
                    }
                }
                yield(listOf("python"))
            }
        }

        val checkScript = plugin.extractResource(
            "check_build_python.py", plugin.buildSubdir())
        var error: String? = null
        var gotStderr = false
        for (bp in bps) {
            val stdout = ByteArrayOutputStream()
            val stderr = ByteArrayOutputStream()
            try {
                plugin.execOps.exec {
                    commandLine(bp)
                    args(checkScript, version)
                    standardOutput = stdout
                    errorOutput = stderr
                }
                return BuildPythonInfo(bp, stdout.toString())
            } catch (e: ExecException) {
                if (stderr.size() > 0 && !gotStderr) {
                    // Prefer stderr over an exception message.
                    error = stderr.toString().trim()
                    gotStderr = true
                } else if (error == null) {
                    // Prefer the error for the original command over the split form.
                    error = e.message ?: e.javaClass.name
                }
            }
        }
        if (bpSetting != null) {
            throw BuildPythonException(
                "$bpSetting is not a valid Python $version command: $error.",
                BUILD_PYTHON_ADVICE)
        } else {
            throw BuildPythonException(
                "Couldn't find Python $version.", BUILD_PYTHON_ADVICE)
        }
    }
}


val BUILD_PYTHON_ADVICE =
    "See https://chaquo.com/chaquopy/doc/current/android.html#buildpython"

class BuildPythonException(val shortMessage: String, suffix: String) :
    GradleException("$shortMessage $suffix")


abstract class OutputDirTask : DefaultTask() {
    @get:OutputDirectory
    abstract val outputDir: DirectoryProperty

    @TaskAction
    open fun run() {
        project.delete(outputDir)
        project.mkdir(outputDir)
    }
}

abstract class AssetDirTask : OutputDirTask() {
    @get:Internal
    val assetDir
        get() = project.file(outputDir).resolve(Common.ASSET_DIR)

    @TaskAction
    override fun run() {
        super.run()
        project.mkdir(assetDir)
    }
}


fun hashAssets(vararg tasks: Provider<AssetDirTask>): JSONObject {
    val json = JSONObject()
    for (task in tasks) {
        hashAssets(json, task.get().assetDir, "")
    }
    return json
}

fun hashAssets(json: JSONObject, dir: File, prefix: String) {
    for (file in dir.listFiles()!!) {
        val path = prefix + file.name
        if (file.isDirectory()) {
            hashAssets(json, file, path + "/")
        } else {
            // These files may be hundreds of megabytes, so read them in chunks.
            val digest = MessageDigest.getInstance("SHA-1")
            file.inputStream().use { stream ->
                val buf = ByteArray(1024 * 1024)
                while (true) {
                    val len = stream.read(buf)
                    if (len > 0) {
                        digest.update(buf, 0, len)
                    } else {
                        break
                    }
                }
            }
            json.put(path, digest.digest().joinToString("") { "%02x".format(it) })
        }
    }
}


// Based on org/gradle/api/internal/file/archive/ZipCopyAction.java. This isn't part of
// the Gradle public API except via the Zip task, which we're not using because we'd
// need to refactor to have one task per ZIP.
//
// The usual alternative is to use ant.zip, but that has other problems:
//   * It only takes simple exclusion patterns, so there's no way to say "exclude .py
//     files which have a corresponding .pyc".
//   * It has no equivalent to preserveFileTimestamps, so we'd have to actually set the
//     timestamps of all the input files.
fun makeZip(tree: FileTree, outFile: File) {
    ZipArchiveOutputStream(outFile).use { zip ->
        // UTF-8 filename encoding is apparently on by default on Linux and off by
        // default on Windows: this alters the resulting ZIP file even if all filenames
        // are ASCII.
        zip.setEncoding("UTF-8")

        // This is the same timestamp used by Gradle's preserveFileTimestamps setting.
        // The UTC timestamp generated here will vary according to the current timezone,
        // but the local time will be constant, and that's what gets stored in the ZIP.
        val timestamp = GregorianCalendar(1980, Calendar.FEBRUARY, 1, 0, 0, 0)
            .getTimeInMillis()

        tree.visit(object : ReproducibleFileVisitor {
            override fun isReproducibleFileOrder(): Boolean {
                return true
            }
            override fun visitDir(details: FileVisitDetails) {
                val entry = ZipArchiveEntry(details.path + "/")
                entry.setTime(timestamp)
                zip.putArchiveEntry(entry)
                zip.closeArchiveEntry()
            }
            override fun visitFile(details: FileVisitDetails) {
                val entry = ZipArchiveEntry(details.path)
                entry.setTime(timestamp)
                zip.putArchiveEntry(entry)
                details.copyTo(zip)
                zip.closeArchiveEntry()
            }
        })
    }
}


fun assertExists(f: File) : File {
    if (!f.exists()) {
        throw GradleException("$f does not exist")
    }
    return f
}


// Helpers for building argument lists with a similar syntax to ExecSpec.
fun MutableList<String>.args(vararg args: Any) =
    this.args(args.asList())

fun MutableList<String>.args(args: Iterable<Any>) {
    for (arg in args) {
        add(arg.toString())
    }
}
