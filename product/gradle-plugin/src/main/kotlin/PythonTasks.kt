package com.chaquo.python

import com.android.build.api.variant.*
import com.chaquo.python.internal.*
import com.chaquo.python.internal.Common.assetZip
import com.chaquo.python.internal.Common.osName
import org.apache.commons.compress.archivers.zip.*
import org.gradle.api.*
import org.gradle.api.file.*
import org.gradle.api.model.*
import org.gradle.api.provider.*
import org.gradle.api.provider.Property
import org.gradle.api.provider.Provider
import org.gradle.api.tasks.*
import org.gradle.api.tasks.Optional
import org.gradle.kotlin.dsl.*
import org.gradle.process.*
import org.gradle.process.internal.*
import org.json.*
import java.io.*
import java.nio.file.*
import java.security.*
import java.util.*
import javax.inject.*
import kotlin.reflect.*


class TaskBuilder(
    val plugin: PythonPlugin, val variant: Variant, val python: PythonExtension
) {
    val project = plugin.project

    fun build() {
        val abis = plugin.getAbis(variant, python)
        createConfigs(abis)

        val buildPackagesTask = registerBuildPackagesTask()
        val srcTask = registerSrcTask(buildPackagesTask)
        val reqsTask = registerReqsTask(buildPackagesTask, abis)
        registerProxyTask(buildPackagesTask, srcTask, reqsTask)

        val srcAssetsTask = registerZipTask("source", srcTask, SrcAssetsTask::class)
        val reqsAssetsTask =
            registerZipTask("requirements", reqsTask, ReqsAssetsTask::class)
        val miscAssetsTask = registerMiscAssetsTask(abis)
        registerBuildAssetsTask(srcAssetsTask, reqsAssetsTask, miscAssetsTask)

        registerJniLibsTask(abis)
    }

    fun createConfigs(abis: List<String>) {
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

    fun registerBuildPackagesTask(): Provider<BuildPackagesTask> {
        val findCommandTask = registerTask(
            "find", "command", FindPythonCommandTask::class
        ) {
            version.set(python.version)
            bpSetting.set(python.buildPython)
            outputDir.set(plugin.buildSubdir("findCommand", variant))

            // We could add the executable search directories as inputs, but that still
            // wouldn't detect changes in things like the availablility of versions for
            // the `py` command.
            outputs.upToDateWhen { false }
        }

        return registerTask("extract", "buildPackages", BuildPackagesTask::class) {
            findCommandDir.set(findCommandTask.get().outputDir)

            // Keep the path short to avoid the the Windows 260-character limit.
            outputDir.set(plugin.buildSubdir("env", variant))
        }
    }

    abstract class BuildPackagesTask : OutputDirTask() {
        @get:InputFiles abstract val findCommandDir: DirectoryProperty

        override fun writeOutput(outputDir: File) {
            val findCommandDir = file(findCommandDir)
            val errorFile = findCommandDir.resolve(ERROR_FILENAME)
            if (errorFile.exists()) {
                copy {
                    from(errorFile)
                    into(outputDir)
                }
                return
            }

            val command =
                findCommandDir.resolve(COMMAND_FILENAME).readText().split("\n")
            exec {
                commandLine(command)
                args("-m", "venv", "--without-pip", outputDir)
            }

            val zipPath = extractResource("build-packages.zip", outputDir)
            copy {
                from(zipTree(zipPath))
                into(findSitePackages(outputDir))
            }
            delete(zipPath)

            // Pre-generate the __pycache__ directories to avoid the outputDir
            // contents changing and breaking the up to date checks.
            exec {
                commandLine(command)
                args("-Wignore", "-m", "compileall", "-qq", outputDir)
            }
        }

        fun findSitePackages(outputDir: File): File {
            val libPythonDir = if (osName() == "windows") {
                assertExists(outputDir.resolve("Lib"))
            } else {
                val libDir = outputDir.resolve("lib")
                val pythonDirs = listFiles(libDir).filter {
                    it.name.startsWith("python")
                }
                if (pythonDirs.size != 1) {
                    throw GradleException(
                        "found ${pythonDirs.size} python directories in $libDir")
                }
                pythonDirs[0]
            }
            return assertIsDir(libPythonDir.resolve("site-packages"))
        }
    }

    fun registerSrcTask(buildPackagesTask: Provider<BuildPackagesTask>) =
        registerTask("merge", "sources", SrcTask::class) {
            configure(buildPackagesTask, python, python.pyc.src)

            for (name in sourceSetNames()) {
                val dirSet = plugin.extension.sourceSets.findByName(name)
                if (dirSet != null) {
                    for (srcDir in dirSet.srcDirs) {
                        srcTrees.add(fileTree(srcDir).apply {
                            exclude(dirSet.excludes)
                            include(dirSet.includes)
                        })
                    }
                }
            }
            outputDir.set(plugin.buildSubdir("sources", variant))
        }

    abstract class SrcTask : BuildPythonTask() {
        @get:InputFiles abstract val srcTrees: ListProperty<FileTree>

        override fun writeOutput(outputDir: File) {
            copy {
                for (tree in srcTrees.get()) {
                    from(tree)
                }
                duplicatesStrategy = DuplicatesStrategy.FAIL  // Overridden below

                exclude("**/*.pyc", "**/*.pyo")
                exclude("**/*.egg-info")  // See ExtractPackages.test_change
                into(outputDir)

                // Allow duplicates for empty files (e.g. __init__.py)
                eachFile {
                    if (file.length() == 0L) {
                        val destFile = outputDir.resolve(path)
                        if (destFile.exists() && destFile.length() == 0L) {
                            duplicatesStrategy = DuplicatesStrategy.INCLUDE
                        }
                    }
                }
            }
            compilePyc()
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

    fun registerReqsTask(
        buildPackagesTask: Provider<BuildPackagesTask>, abis: List<String>
    ) = registerTask("install", "requirements", ReqsTask::class) {
            configure(buildPackagesTask, python, python.pyc.pip)

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

            if (!reqsArgs.isEmpty()) {
                args.set(ArrayList<String>().apply {
                    args("-m", "chaquopy.pip_install")
                    args("--target", project.file(outputDir))
                    args("--android-abis", *abis.toTypedArray())
                    args("--min-api-level", variant.minSdkVersion.apiLevel)
                    args(reqsArgs)
                    args("--")
                    args(python.pip.options)
                })
            }
            this.abis.set(abis)
        }

    abstract class ReqsTask : BuildPythonTask() {
        @get:Input abstract val args: ListProperty<String>
        @get:Input abstract val abis: ListProperty<String>

        override fun writeOutput(outputDir: File) {
            val args = args.get()
            if (!args.isEmpty()) {
                execBuildPython(args)
                compilePyc()
            } else {
                // Create empty directories so we have something to zip.
                for (subdir in listOf(Common.ABI_COMMON) + abis.get()) {
                    mkdir(outputDir.resolve(subdir))
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
            file = baseDir.resolve(req)
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

    fun registerProxyTask(
        buildPackagesTask: Provider<BuildPackagesTask>,
        srcTask: Provider<SrcTask>,
        reqsTask: Provider<ReqsTask>
    ) {
        registerGenerateTask(variant.sources.java!!, "proxies", ProxyTask::class) {
            configure(buildPackagesTask, python)
            inputs.files(reqsTask, srcTask)
            outputDir.set(plugin.buildSubdir("proxies", variant))

            if (!python.staticProxy.isEmpty()) {
                args.set(ArrayList<String>().apply {
                    args("-m", "chaquopy.static_proxy")
                    args("--path",
                        listOf(
                            project.file(srcTask.get().outputDir),
                            project.file(reqsTask.get().outputDir).resolve("common")
                        ).joinToString(File.pathSeparator))
                    args("--java", project.file(outputDir))
                    args(python.staticProxy)
                })
            }
        }
    }

    abstract class ProxyTask : BuildPythonTask() {
        @get:Input abstract val args: ListProperty<String>

        override fun writeOutput(outputDir: File) {
            val args = args.get()
            if (!args.isEmpty()) {
                execBuildPython(args)
            }
        }
    }

    abstract class PythonZipTask : AssetDirTask() {
        @get:InputFiles abstract val inputDir: DirectoryProperty
        @get:Input abstract val extractPackages: SetProperty<String>

        fun makeZip(dir: File, assetDir: File, zipName: String) {
            makeZip(
                fileTree(dir).matching { exclude(::excludePy) },
                assetDir.resolve(zipName)
            )
        }

        // Exclude .py files which have a corresponding .pyc, unless unless they’re
        // included in extractPackages.
        fun excludePy(fte: FileTreeElement) =
            if (fte.name.endsWith(".py") &&
                File(fte.file.parent, fte.name + "c").exists()
            ) {
                ! extractPackages.get().any {
                    it == "*" || fte.path.replace("/", ".").startsWith(it + ".")
                }
            } else false
    }

    fun <T: PythonZipTask> registerZipTask(
        name: String, inputTask: Provider<out OutputDirTask>, cls: KClass<T>
    ) = registerAssetTask(name, cls) {
            inputDir.set(inputTask.get().outputDir)
            extractPackages.set(python.extractPackages)
        }

    abstract class SrcAssetsTask : PythonZipTask() {
        override fun writeAssets(assetDir: File) {
            makeZip(file(inputDir), assetDir, assetZip(Common.ASSET_APP))
        }
    }

    abstract class ReqsAssetsTask : PythonZipTask() {
        override fun writeAssets(assetDir: File) {
            for (subdir in listFiles(file(inputDir))) {
                makeZip(
                    subdir, assetDir, assetZip(Common.ASSET_REQUIREMENTS, subdir.name)
                )
            }
        }
    }

    fun registerMiscAssetsTask(abis: List<String>) =
        registerAssetTask("misc", MiscAssetsTask::class) {
            version.set(python.version)
            this.abis.set(abis)
            runtimeBootstrap.from(plugin.getConfig("runtimeBootstrap", variant))
            runtimeModules.from(plugin.getConfig("runtimeModules", variant))
            targetStdlib.from(plugin.getConfig("targetStdlib", variant))
            targetNative.from(plugin.getConfig("targetNative", variant))
        }

    abstract class MiscAssetsTask : AssetDirTask() {
        @get:Input abstract val version: Property<String>
        @get:Input abstract val abis: ListProperty<String>
        @get:InputFiles abstract val runtimeBootstrap: ConfigurableFileCollection
        @get:InputFiles abstract val runtimeModules: ConfigurableFileCollection
        @get:InputFiles abstract val targetStdlib: ConfigurableFileCollection
        @get:InputFiles abstract val targetNative: ConfigurableFileCollection

        override fun writeAssets(assetDir: File) {
            copy {
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
                "_random.*",  // random < tempfile < importer
                "_sha512.*",  // random < tempfile < importer
                "_struct.*",  // zipfile < importer
                "binascii.*",  // zipfile < importer
                "math.*",  // datetime < calendar < importer
                "mmap.*",  // elftools < importer
                "zlib.*"  // zipimport
            )

            val versionParts = version.get().split(".")
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
            if (versionInt >= 314) {
                BOOTSTRAP_NATIVE_STDLIB.removeAll(listOf(
                    "_datetime.*", "_opcode.*"
                ))
            }

            for (abi in abis.get()) {
                copy {
                    from(zipTree(resolveArtifact(targetNative, abi)))
                    include("lib-dynload/**")
                    into(assetDir)
                }
                makeZip(fileTree("$assetDir/lib-dynload/$abi")
                    .matching { exclude(BOOTSTRAP_NATIVE_STDLIB) },
                    File(assetDir, assetZip(Common.ASSET_STDLIB, abi)))

                val bootstrapDir = "$assetDir/${Common.ASSET_BOOTSTRAP_NATIVE}/$abi"
                copy {
                    from("$assetDir/lib-dynload/$abi")
                    include(BOOTSTRAP_NATIVE_STDLIB)
                    into(bootstrapDir)
                }
                delete("$assetDir/lib-dynload")

                copy {
                    fromRuntimeArtifact(runtimeModules, abi)
                    into("$bootstrapDir/java")
                }
            }
            extractResource(Common.ASSET_CACERT, assetDir)
        }
    }

    fun registerBuildAssetsTask(vararg tasks: Provider<out AssetDirTask>) =
        registerAssetTask("build", BuildAssetsTask::class) {
            version.set(python.version)
            for (task in tasks) {
                inputDirs.from(task.get().outputDir)
            }
            extractPackages.set(python.extractPackages)
        }

        abstract class BuildAssetsTask : AssetDirTask() {
            @get:Input abstract val version: Property<String>
            @get:InputFiles abstract val inputDirs: ConfigurableFileCollection
            @get:Input abstract val extractPackages: SetProperty<String>

            override fun writeAssets(assetDir: File) {
                val buildJson = JSONObject()
                buildJson.put("python_version", version.get())
                buildJson.put("assets", JSONObject().apply {
                    for (dir in inputDirs) {
                        hashAssets(this, dir.resolve(Common.ASSET_DIR), "")
                    }
                })
                buildJson.put("extract_packages", JSONArray(extractPackages.get()))
                File(assetDir, Common.ASSET_BUILD_JSON).writeText(buildJson.toString(4))
            }
        }

    fun <T: AssetDirTask> registerAssetTask(
        name: String, cls: KClass<T>, configure: T.() -> Unit
    ) = registerGenerateTask(
        variant.sources.assets!!, "${name}Assets", cls
    ) {
        outputDir.set(plugin.buildSubdir("assets/$name", variant))
        configure()
    }

    fun registerJniLibsTask(abis: List<String>) =
        registerGenerateTask(variant.sources.jniLibs!!, "jniLibs", JniLibsTask::class) {
            this.abis.set(abis)
            targetNative.from(plugin.getConfig("targetNative", variant))
            runtimeJni.from(plugin.getConfig("runtimeJni", variant))
            outputDir.set(plugin.buildSubdir("jniLibs", variant))
        }

    abstract class JniLibsTask : OutputDirTask() {
        @get:Input abstract val abis: ListProperty<String>
        @get:InputFiles abstract val targetNative: ConfigurableFileCollection
        @get:InputFiles abstract val runtimeJni: ConfigurableFileCollection

        override fun writeOutput(outputDir: File) {
            for (abi in abis.get()) {
                // Copy jniLibs/<arch>/ in the ZIP to jniLibs/<variant>/<arch>/ in
                // the build directory.
                // (https://discuss.gradle.org/t/copyspec-support-for-moving-files-directories/7412/1)
                copy {
                    from(zipTree(resolveArtifact(targetNative, abi)))
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

                copy {
                    fromRuntimeArtifact(runtimeJni, abi)
                    into(outputDir.resolve(abi))
                }
            }
        }
    }

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

    abstract class BuildPythonTask : OutputDirTask() {
        @get:InputFiles abstract val buildVenv: DirectoryProperty
        @get:Input abstract val version: Property<String>
        @get:Input @get:Optional abstract val pyc: Property<Boolean>

        fun configure(
            buildPackagesTask: Provider<BuildPackagesTask>,
            python: PythonExtension,
            pyc: Boolean? = null
        ) {
            buildVenv.set(buildPackagesTask.get().outputDir)
            version.set(python.version)
            this.pyc.set(pyc)
        }

        fun execBuildPython(args: List<String>) {
            val buildVenv = file(buildVenv)
            val errorFile = buildVenv.resolve(ERROR_FILENAME)
            if (errorFile.exists()) {
                throw ExecException(errorFile.readText())
            }

            exec {
                executable(
                    buildVenv.resolve(
                        if (osName() == "windows") "Scripts/python.exe" else "bin/python"
                    )
                )
                this.args(args)
            }
        }

        // We can't remove the .py files here because the static proxy generator needs
        // them. Instead, they'll be excluded when we call makeZip.
        fun compilePyc() {
            val setting = pyc.getOrNull()
            if (setting != false) {
                try {
                    execBuildPython(ArrayList<String>().apply {
                        args("-m", "chaquopy.pyc")
                        args("--python", version.get())
                        args("--quiet")
                        if (setting != true) {
                            args("--warning")
                        }
                        args(outputDir.get())
                    })
                } catch (e: ExecException) {
                    if (setting == true) {
                        throw e
                    } else {
                        // Messages should be formatted the same as in chaquopy.pyc.
                        warn(
                            "Failed to compile to .pyc format: " +
                            e.message!!.replace("#buildpython", "#android-bytecode")
                        )
                    }
                }
            }
        }
    }

    fun <T: Task> registerTask(
        verb: String, noun: String, cls: KClass<T>, configure: T.() -> Unit
    ): TaskProvider<T> {
        // This matches the format of the AGP's own task names.
        return project.tasks.register(
            "$verb${variant.name.capitalize()}Python${noun.capitalize()}",
            cls, configure)
    }
}


fun resolveArtifact(fc: FileCollection, abi: String? = null): File {
    if (abi == null) {
        return fc.singleFile
    }
    for (file in fc.files) {
        if (!parseArtifact(file).versionClassifier.endsWith("-$abi")) {
            continue
        }
        return file
    }
    throw GradleException("artifact not found for ABI $abi)")
}


fun CopySpec.fromRuntimeArtifact(
    fc: FileCollection, abi: String? = null
) {
    val file = resolveArtifact(fc, abi)
    val parsed = parseArtifact(file)
    from(file) {
        rename { "${parsed.name}.${parsed.ext}" }
    }
}


fun parseArtifact(file: File): ParsedArtifact {
    val match =
        Regex("""(\w+)-(.+)\.(\w+)""").matchEntire(file.name)
        ?: throw GradleException("Failed to parse artifact filename '${file.name}'")
    val (name, versionClassifier, ext) = match.destructured
    return ParsedArtifact(name, versionClassifier, ext)
}

data class ParsedArtifact(
    val name: String, val versionClassifier: String, val ext: String
)


abstract class PythonTask : DefaultTask() {
    @get:Inject abstract val objects: ObjectFactory
    @get:Inject abstract val layout: ProjectLayout
    @get:Inject abstract val execOps: ExecOperations
    @get:Inject abstract val fsOps: FileSystemOperations
    @get:Inject abstract val archiveOps: ArchiveOperations

    // Replacements for Project methods, which aren't available at execution time when
    // the configuration cache is enabled.
    fun file(path: File) =
        layout.projectDirectory.asFile.resolve(path)

    fun file(path: String) =
        file(File(path))

    fun file(path: Provider<out FileSystemLocation>) =
        file(path.get().asFile)

    fun fileTree(path: Any) =
        objects.fileTree().from(path)

    fun mkdir(path: File) =
        Files.createDirectories(path.toPath()).toFile()

    fun copy(configure: CopySpec.() -> Unit) =
        fsOps.copy(configure)

    fun delete(path: Any) =
        fsOps.delete { delete(path) }

    fun zipTree(path: Any) =
        archiveOps.zipTree(path)

    fun exec(configure: ExecSpec.() -> Unit) =
        execOps.exec(configure)
}


// This task returns either a Python command line, or an error message explaining why
// it couldn't find one. It also returns the stdout of check_build_python.py, so we can
// detect when the build venv needs to be rebuilt.
//
// However, Gradle provides no easy way for a task to output anything other than files.
// Some people suggest connecting @Internal properties of the first task to to @Input
// properties of the second one, but the Provider documentation doesn't clearly state
// that this would be safe when the configuration cache is computing and storing
// property values. So let's just go with the flow and write everything to files.
abstract class FindPythonCommandTask : OutputDirTask() {
    @get:Input abstract val version: Property<String>
    @get:Input @get:Optional abstract val bpSetting: ListProperty<String>

    override fun writeOutput(outputDir: File) {
        val version = version.get()
        val bpSetting = bpSetting.getOrNull()
        val bps = sequence {
            if (bpSetting != null) {
                yield(bpSetting)
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

        val checkScript = extractResource("check_build_python.py", outputDir)
        var error: String? = null
        var gotStderr = false
        for (bp in bps) {
            val stdout = ByteArrayOutputStream()
            val stderr = ByteArrayOutputStream()
            try {
                val bpResolved = ArrayList<String>().apply {
                    add(findExecutable(bp[0]).toString())
                    addAll(bp.subList(1, bp.size))
                }
                exec {
                    commandLine(bpResolved)
                    args(checkScript, version)
                    standardOutput = stdout
                    errorOutput = stderr
                }
                outputDir.resolve(COMMAND_FILENAME).writeText(
                    bpResolved.joinToString("\n")
                )
                outputDir.resolve(STDOUT_FILENAME).writeBytes(stdout.toByteArray())
                return
            } catch (e: ExecException) {
                // Prefer stderr over an exception message.
                if (stderr.size() > 0 && !gotStderr) {
                    error = stderr.toString().trim()
                    gotStderr = true

                    // Prefer an earlier error over a later one.
                } else if (error == null) {
                    error = e.message ?: e.javaClass.name
                }
            }
        }
        outputDir.resolve(ERROR_FILENAME).writeText(
            if (bpSetting != null) {
                "$bpSetting is not a valid Python $version command: $error. " +
                BUILD_PYTHON_ADVICE
            } else {
                "Couldn't find Python $version. $BUILD_PYTHON_ADVICE"
            }
        )
    }

    // To reduce differences between platforms, and make testing easier, we resolve
    // executables to absolute paths manually (#1411).
    fun findExecutable(executable: String): File {
        var execFile = file(executable)
        if (execFile.exists()) {
            return execFile
        } else {
            // If the executable contains no slashes, search the PATH.
            if (File.separator in executable || "/" in executable) {
                throw ExecException("'$execFile' does not exist")
            }

            // For consistency between machines, we don't use the PATHEXT variable.
            val exts = mutableListOf("")
            if (osName() == "windows") {
                exts += listOf(".exe", ".bat")
            }

            outer@ for (dir in System.getenv("PATH").split(File.pathSeparator)) {
                for (ext in exts) {
                    execFile = File(dir, executable + ext)
                    if (execFile.exists()) {
                        break@outer
                    }
                }
            }
            if (execFile.exists()) {
                return execFile
            } else {
                throw ExecException(
                    "Couldn't find '$executable' on the PATH " +
                    "or in the project directory")
            }
        }
    }
}


val BUILD_PYTHON_ADVICE =
    "See https://chaquo.com/chaquopy/doc/current/android.html#buildpython."

val ERROR_FILENAME = "error.txt"
val COMMAND_FILENAME = "command.txt"
val STDOUT_FILENAME = "stdout.txt"

abstract class OutputDirTask : PythonTask() {
    @get:OutputDirectory abstract val outputDir: DirectoryProperty

    @TaskAction fun run() {
        val outputDir = file(outputDir)
        delete(outputDir)
        mkdir(outputDir)
        writeOutput(outputDir)
    }

    abstract fun writeOutput(outputDir: File)
}


abstract class AssetDirTask : OutputDirTask() {
    final override fun writeOutput(outputDir: File) {
        val assetDir = outputDir.resolve(Common.ASSET_DIR)
        mkdir(assetDir)
        writeAssets(assetDir)
    }

    abstract fun writeAssets(assetDir: File)
}


fun hashAssets(json: JSONObject, dir: File, prefix: String) {
    for (file in listFiles(dir)) {
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

fun assertIsDir(f: File) : File {
    assertExists(f)
    if (!f.isDirectory()) {
        throw GradleException("$f is not a directory")
    }
    return f
}

fun listFiles(dir: File): Array<File> {
    assertIsDir(dir)
    return dir.listFiles()!!
}


// Helpers for building argument lists with a similar syntax to ExecSpec.
fun MutableList<String>.args(vararg args: Any) =
    this.args(args.asList())

fun MutableList<String>.args(args: Iterable<Any>) {
    for (arg in args) {
        add(arg.toString())
    }
}
