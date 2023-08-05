package com.chaquo.python

import com.android.build.api.dsl.*
import com.android.build.api.variant.*
import com.chaquo.python.internal.*
import org.gradle.api.*
import org.gradle.api.artifacts.*
import org.gradle.api.initialization.dsl.*
import org.gradle.api.plugins.*
import org.gradle.kotlin.dsl.*
import org.gradle.util.*
import java.io.*
import java.nio.file.*
import java.nio.file.StandardCopyOption.REPLACE_EXISTING
import kotlin.properties.Delegates.notNull


class PythonPlugin : Plugin<Project> {

    // Load dependencies from the same buildscript context as the Chaquopy plugin
    // itself, so they'll come from the same repository.
    val pluginInfo by lazy { findPlugin("com.chaquo.python", "gradle") }
    val buildscript by lazy { pluginInfo.buildscript }

    lateinit var project: Project
    var isLibrary by notNull<Boolean>()
    lateinit var android: CommonExtension<*, *, *, *>
    lateinit var extension: ChaquopyExtension
    val variants = ArrayList<Variant>()

    override fun apply(project: Project) {
        this.project = project

        for (moduleType in listOf("application", "library")) {
            project.pluginManager.withPlugin("com.android.$moduleType") {
                checkAgpVersion()
                isLibrary = moduleType == "library"
                android = project.extensions.getByType(CommonExtension::class)

                val proguardFile = extractResource("proguard-rules.pro", buildSubdir())
                android.defaultConfig.proguardFile(proguardFile)
                if (isLibrary) {
                    (android.defaultConfig as LibraryDefaultConfig)
                        .consumerProguardFile(proguardFile)
                }

                createDsl()
                createDependencies()

                // Work around https://youtrack.jetbrains.com/issue/KT-25290 by using
                // the non-generic subclasses of AndroidComponentsExtension.
                val components =
                    project.extensions.getByType(AndroidComponentsExtension::class)
                val selector = components.selector().all()
                try {
                    (components as ApplicationAndroidComponentsExtension).onVariants(
                        selector, ::onVariant)
                } catch (e: ClassCastException) {
                    (components as LibraryAndroidComponentsExtension).onVariants(
                        selector, ::onVariant)
                }

                // We need to look up some AGP tasks by name (see extendMergeTask),
                // but they don't exist yet in onVariant.
                project.afterEvaluate {
                    variants.forEach(::afterVariant)
                }
            }
        }
    }

    // androidComponents has a version number property starting from AGP 7.0, but we
    // still need to be able to give a useful error message when running with older
    // versions.
    fun checkAgpVersion() {
        val version = VersionNumber.parse(
            findPlugin("com.android.tools.build", "gradle").version)
        val minVersion = VersionNumber.parse(Common.MIN_AGP_VERSION)
        if (version < minVersion) {
            throw GradleException(
                "This version of Chaquopy requires Android Gradle plugin version " +
                "$minVersion or later. Please edit the version of " +
                "com.android.application, com.android.library or " +
                "com.android.tools.build:gradle in your top-level build.gradle " +
                "file. See https://chaquo.com/chaquopy/doc/current/versions.html.")
        }
    }

    data class PluginInfo(
        val buildscript: ScriptHandler, val version: String)

    fun findPlugin(group: String, name: String): PluginInfo {
        var p: Project? = project
        while (p != null) {
            for (art in p.buildscript.configurations.getByName("classpath")
                 .resolvedConfiguration.resolvedArtifacts) {
                val dep = art.moduleVersion.id
                if (dep.group == group  &&  dep.name == name) {
                    return PluginInfo(p.buildscript, dep.version)
                }
            }
            p = p.parent
        }
        throw GradleException("Failed to find plugin $group:$name")
    }

    // AGP has a registerExtension API for adding custom DSL within the `android` block,
    // but as of AGP 8.1 and Gradle 8.0, it doesn't generate Kotlin accessors. AGP 7.2
    // adds a registerSourceType API, but I expect that has the same problem. Instead,
    // we put all our DSL within a separate project-level extension.
    //
    // The old DSL, which looks fine in Groovy but requires lots of casting in Kotlin,
    // takes advantage of the fact that DefaultConfig and AndroidSourceSet are actually
    // ExtensionAware at runtime even if they're not documented as such, because they're
    // created as a _Decorated subclass using ObjectFactory.newInstance.
    fun createDsl() {
        extension = ChaquopyExtension(project)
        project.extensions.add("chaquopy", extension)
        (android.defaultConfig as ExtensionAware).extensions.add(  // Old DSL
            "python", extension.defaultConfig)

        android.productFlavors.all {
            val python = extension.productFlavors.maybeCreate(name)
            (this as ExtensionAware).extensions.add("python", python)  // Old DSL
        }

        android.sourceSets.all {
           val dirSet = extension.sourceSets.maybeCreate(name)
           (this as ExtensionAware).extensions.add("python", dirSet)  // Old DSL
        }
   }

    fun createDependencies() {
        val runtimeJava = addRuntimeDependency("java", "chaquopy_java.jar")

        // Use `api` rather than `implementation` so it's available to dynamic feature
        // modules.
        //
        // Can't depend directly on runtimeJava, because "Currently you can only declare
        // dependencies on configurations from the same project."
        project.dependencies.add("api", project.files(runtimeJava))
    }

    fun addDependency(fullConfig: String, dep: Map<String, String>): Configuration {
        buildscript.apply {
            val config = configurations.maybeCreate(fullConfig)
            dependencies.add(config.name, dep)
            return config
        }
    }

    fun addRuntimeDependency(
        config: String, filename: String, variant: Variant? = null,
        python: PythonExtension? = null, abi: String? = null
    ) =
        addDependency(
            configName("runtime${config.capitalize()}", variant),
            HashMap<String, String>().apply {
                val dotPos = filename.lastIndexOf(".")
                put("group", "com.chaquo.python.runtime")
                put("name", filename.substring(0, dotPos))
                put("version", pluginInfo.version)
                put("ext", filename.substring(dotPos + 1))
                if (python != null) {
                    put("classifier", runtimeClassifier(python, abi))
                }
            }
        )

    fun addTargetDependency(
        config: String, variant: Variant, python: PythonExtension, classifier: String
    ) =
        addDependency(
            configName("target${config.capitalize()}", variant),
            HashMap<String, String>().apply {
                val entry = pythonVersionInfo(python.version)
                put("group", "com.chaquo.python")
                put("name", "target")
                put("version", "${entry.key}-${entry.value}")
                put("classifier", classifier)
                put("ext", "zip")
            }
        )

    fun getConfig(name: String, variant: Variant) =
        buildscript.configurations.getByName(configName(name, variant))

    // This matches the format of the AGP's own configuration names.
    fun configName(name: String, variant: Variant? = null) =
        "python${(variant?.name ?: "").capitalize()}${name.capitalize()}"

    fun onVariant(variant: Variant) {
        if (variant.minSdkVersion.apiLevel < Common.MIN_SDK_VERSION) {
            throw GradleException(
                "Variant '${variant.name}': This version of Chaquopy requires " +
                "minSdkVersion ${Common.MIN_SDK_VERSION} or higher. See " +
                "https://chaquo.com/chaquopy/doc/current/versions.html.")
        }
        variants.add(variant)
    }

    fun afterVariant(variant: Variant) {
        // TODO: merge flavors
        val python = extension.defaultConfig
        TaskFactory(this).createTasks(variant, python)
    }

    fun extractResource(name: String, targetDir: File): File {
        project.mkdir(targetDir)
        val outFile = File(targetDir, File(name).name)
        val tmpFile = File("${outFile.path}.tmp")
        val stream = javaClass.getResourceAsStream(name)
            ?: throw IOException("getResourceAsString failed for '$name'")
        Files.copy(stream, tmpFile.toPath(), REPLACE_EXISTING)
        project.delete(outFile)
        if (! tmpFile.renameTo(outFile)) {
            throw IOException("Failed to create '$outFile'")
        }
        return outFile
    }

    fun buildSubdir(name: String? = null, variant: Variant? = null): File {
        var result = File(project.buildDir, "python")
        if (name != null) {
            result = File(result, name)
            if (variant != null) {
                result = File(result, variant.name)
            }
        }
        return result
    }
}


fun runtimeClassifier(python: PythonExtension, abi: String? = null): String {
    var classifier = python.version
    if (abi != null) {
        classifier += "-$abi"
    }
    return classifier
}

fun pythonVersionInfo(version: String): Map.Entry<String, String> {
    for (entry in Common.PYTHON_VERSIONS.entries) {
        if (entry.key.startsWith(version)) {
            return entry
        }
    }
    // Since the version has already been validated by PythonExtension.version, this
    // should be impossible.
    throw GradleException(
        "Failed to find information for Python version '$version'.")
}
