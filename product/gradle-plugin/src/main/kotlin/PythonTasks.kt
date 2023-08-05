package com.chaquo.python

import com.android.build.api.variant.*
import com.chaquo.python.internal.*
import com.chaquo.python.internal.Common.assetZip
import org.apache.commons.compress.archivers.zip.*
import org.gradle.api.*
import org.gradle.api.artifacts.*
import org.gradle.api.file.*
import org.gradle.api.provider.Provider
import org.gradle.api.tasks.*
import org.gradle.kotlin.dsl.*
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

    fun build() {
        createConfigs()
        val srcTask = createSrcTask()
        val reqsTask = createReqsTask()
        createProxyTask(srcTask, reqsTask)
        createAssetsTasks(srcTask, reqsTask)
        createJniLibsTasks()
    }

    fun createConfigs() {
        plugin.addRuntimeDependency(
            "bootstrap", assetZip(Common.ASSET_BOOTSTRAP), variant, python)
        plugin.addTargetDependency(
            "stdlib", variant, python,
            if (python.pyc.stdlib!!) "stdlib-pyc" else "stdlib")

        for (abi in abis) {
            if (! Common.ABIS.contains(abi)) {
                throw GradleException(
                    "Variant '${variant.name}': Chaquopy does not support the ABI " +
                    "'$abi'. Supported ABIs are ${Common.ABIS}.")
            }
            plugin.addRuntimeDependency(
                "jni", "libchaquopy_java.so", variant, python, abi)
            plugin.addRuntimeDependency(
                "modules", "chaquopy.so", variant, python, abi)
            plugin.addTargetDependency("native", variant, python, abi)
        }
    }

    /*
    * TODO sourceSets - all we actually need is their names, which can easily be
    * generated from productFlavors/buildType.
    */
    fun createSrcTask() =
        registerTask("merge", "sources") {
            destinationDir = plugin.buildSubdir("sources", variant)
        }

    fun createReqsTask() =
        registerTask("generate", "requirements") {
            destinationDir = plugin.buildSubdir("requirements", variant)
            doLast {
                for (subdirName in listOf(Common.ABI_COMMON) + abis) {
                    val subdir = File(destinationDir, subdirName)
                    project.mkdir(subdir)
                }
            }
        }

    /*
    * TODO The stable API to add Java source files is variant.sources, which isn't
    * available in our current minimum AGP version (see extendMergeTask). So we use the
    * deprecated API instead.
    */
    fun createProxyTask(
        srcTask: Provider<OutputDirTask>, reqsTask: Provider<OutputDirTask>
    ) {
    }

    fun createAssetsTasks(
        srcTask: Provider<OutputDirTask>, reqsTask: Provider<OutputDirTask>
    ) {
        val excludePy = { fte: FileTreeElement ->
            if (fte.name.endsWith(".py") &&
                File(fte.file.parent, fte.name + "c").exists()
            ) {
                true
                // TODO
//                ! python.extractPackages.any {
//                    fte.path.replace("/", ".").startsWith(it + ".")
//                }
            } else false
        }

        val srcAssetsTask = assetTask("source") {
            inputs.files(srcTask)
            // TODO inputs.property("extractPackages", python.extractPackages)
            doLast {
                makeZip(project.fileTree(srcTask.get().destinationDir)
                            .matching { exclude(excludePy) },
                        File(assetDir, assetZip(Common.ASSET_APP)))
            }
        }

        val reqsAssetsTask = assetTask("requirements") {
            inputs.files(reqsTask)
            // TODO inputs.property("extractPackages", python.extractPackages)
            doLast {
                for (subdir in reqsTask.get().destinationDir.listFiles()!!) {
                    makeZip(
                        project.fileTree(subdir).matching { exclude(excludePy) },
                        File(assetDir, assetZip(Common.ASSET_REQUIREMENTS, subdir.name)))
                }
            }
        }

        val miscAssetsTask = assetTask("misc") {
            val runtimeBootstrap = plugin.getConfig("runtimeBootstrap", variant)
            val runtimeModules = plugin.getConfig("runtimeModules", variant)
            val targetStdlib = plugin.getConfig("targetStdlib", variant)
            val targetNative = plugin.getConfig("targetNative", variant)
            inputs.files(runtimeBootstrap, runtimeModules, targetStdlib, targetNative)

            doLast {
                project.copy {
                    into(assetDir)
                    fromRuntimeArtifact(runtimeBootstrap)
                    from(targetStdlib) {
                        rename { assetZip(Common.ASSET_STDLIB, Common.ABI_COMMON) }
                    }
                }

                // The following stdlib native modules are needed during bootstrap and are
                // pre-extracted by AndroidPlatform so they can be loaded with the
                // standard FileFinder. All other native modules are loaded from a .zip using
                // AssetFinder.
                val BOOTSTRAP_NATIVE_STDLIB = listOf(
                    "_ctypes.so",  // java.primitive and importer
                    "_datetime.so",  // calendar < importer (see test_datetime)
                    "_random.so",  // random < tempfile < zipimport
                    "_sha512.so",  // random < tempfile < zipimport
                    "_struct.so",  // zipfile < importer
                    "binascii.so",  // zipfile < importer
                    "math.so",  // datetime < calendar < importer
                    "mmap.so",  // elftools < importer
                    "zlib.so"  // zipimport
                )

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

        assetTask("build") {
            val tasks = arrayOf(srcAssetsTask, reqsAssetsTask, miscAssetsTask)
            inputs.files(*tasks)
            doLast {
                val buildJson = JSONObject()
                buildJson.put("python_version", python.version)
                buildJson.put("assets", hashAssets(*tasks))
                buildJson.put("extract_packages", JSONArray(/* TODO python.extractPackages */))
                File(assetDir, Common.ASSET_BUILD_JSON).writeText(buildJson.toString(4))
            }
        }

    }

    fun assetTask(
        name: String, configure: AssetDirTask.() -> Unit
    ): Provider<AssetDirTask> {
        val task = registerTask("generate", "${name}Assets", AssetDirTask::class) {
            destinationDir = plugin.buildSubdir("assets/$name", variant)
            configure()
        }

        extendMergeTask(if (plugin.isLibrary) "package" else "merge",
                        "assets", task)
        return task
    }

    // There are a couple of supported APIs for adding content to the APK, but they
    // aren't available in our current minimum AGP version:
    //   * variant.sources supports Java files from AGP 7.2, and assets and native libs
    //     from 7.3.
    //   * variant.artifacts supports Java files and assets from AGP 7.1 (though you
    //     have to compile the Java files yourself), and native libs from 8.1.
    fun <T: OutputDirTask> extendMergeTask(
        verb: String, noun: String, inputTask: Provider<T>
    ) {
        project.tasks.named("$verb${variant.name.capitalize()}${noun.capitalize()}") {
            inputs.files(inputTask)
            val mergeTask = this
            val getOutputDir = mergeTask.javaClass.getMethod("getOutputDir")
            doLast {
                project.copy {
                    from(inputTask.get().destinationDir)
                    into(getOutputDir.invoke(mergeTask) as DirectoryProperty)
                }
            }
        }
    }

    fun createJniLibsTasks() {
        val task = registerTask("generate", "jniLibs") {
            val runtimeJni = plugin.getConfig("runtimeJni", variant)
            val targetNative = plugin.getConfig("targetNative", variant)
            inputs.files(runtimeJni, targetNative)

            destinationDir = plugin.buildSubdir("jniLibs", variant)
            doLast {
                val artifacts = targetNative.resolvedConfiguration.resolvedArtifacts
                for (art in artifacts) {
                    // Copy jniLibs/<arch>/ in the ZIP to jniLibs/<variant>/<arch>/ in
                    // the build directory.
                    // (https://discuss.gradle.org/t/copyspec-support-for-moving-files-directories/7412/1)
                    project.copy {
                        from(project.zipTree(art.file))
                        include("jniLibs/**")
                        into(destinationDir)
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
                        into("$destinationDir/$abi")
                    }
                }
            }
        }
        extendMergeTask("merge", "jniLibFolders", task)
    }

    fun registerTask(
        verb: String, noun: String, configure: OutputDirTask.() -> Unit
    ) = registerTask(verb, noun, OutputDirTask::class, configure)

    fun <T: OutputDirTask> registerTask(
        verb: String, noun: String, cls: KClass<T>, configure: T.() -> Unit
    ): Provider<T> {
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
}


open class OutputDirTask : DefaultTask() {
    @get:OutputDirectory
    lateinit var destinationDir: File
    // TODO rename to outputDir once all uses are converted

    // TODO remove redundant uses of outputs, delete and mkdir
    @TaskAction
    open fun run() {
        project.delete(destinationDir)
        project.mkdir(destinationDir)
    }
}

open class AssetDirTask : OutputDirTask() {
    @get:Internal
    val assetDir
        get() = File(destinationDir, Common.ASSET_DIR)

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
