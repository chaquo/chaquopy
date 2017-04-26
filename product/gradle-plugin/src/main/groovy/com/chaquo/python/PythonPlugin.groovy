package com.chaquo.python

import org.gradle.api.*
import org.gradle.api.plugins.*
import org.gradle.api.tasks.*
import java.nio.file.*

// FIXME unit test everything
// Wrong python version
// Wrong ABIs
// Override by flavor
// Override by multi-flavor
// up to date checks
class PythonPlugin implements Plugin<Project> {
    static final def NAME = "python"

    Project project
    def android

    public void apply(Project project) {
        this.project = project
        if (! project.hasProperty("android")) {
            throw new GradleException("project.android not set. Did you apply plugin "+
                                      "com.android.application before com.chaquo.python?")
        }
        android = project.android

        extend(android.defaultConfig)
        android.productFlavors.whenObjectAdded { extend(it) }
        // I also tried adding it to buildTypes but it had no effect for some reason

        // TODO add "python" source set property

        setupDependencies()

        project.afterEvaluate { afterEvaluate() }
    }

    void extend(ExtensionAware ea) {
        ea.extensions.create(NAME, PythonExtension)
    }

    void setupDependencies() {
        project.repositories { maven { url "http://chaquo.com/maven" } }

        def filename = "runtime/chaquopy-runtime.jar"
        def outFile = new File(pythonGenDir(), filename)
        project.delete(outFile)     // It might be an old version
        project.mkdir(outFile.parent)
        getClass().getResourceAsStream("/$filename").withStream { is ->
            def tmpFile = new File(outFile.parent, "${outFile.name}.tmp")
            Files.copy(is, tmpFile.toPath())
            if (! tmpFile.renameTo(outFile)) {
                throw new IOException("Failed to create $outFile")
            }
        }
        project.dependencies {
            compile project.files(outFile)
        }
    }

    void afterEvaluate() {
        for (variant in android.applicationVariants) {
            def python = new PythonExtension()
            python.mergeFrom(android.defaultConfig)
            for (flavor in variant.getProductFlavors().reverse()) {
                python.mergeFrom(flavor)
            }
            if (python.version == null) {
                throw new GradleException("python.version not set for variant '$variant.name'. " +
                                          "You may want to add it to defaultConfig.")
            }

            createTargetConfigs(variant, python)
            createSourceTask(variant, python)
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
            project.dependencies.add(abiConfig, targetDependency(python.version, abi))
        }
    }

    String targetDependency(String version, String classifier) {
        /** Following the Maven version number format, this is the "build number". */
        final def TARGET_VERSION_SUFFIX = "-0"
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
            // Replicate the accumulation behaviour of MergedNdkConfig.append
            if (flavor.ndk.abiFilters) {
                abis.addAll(flavor.ndk.abiFilters)
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

    void createSourceTask(variant, PythonExtension python) {
        // TODO python{} parameters may need to be task inputs as well
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
    }

    void createAssetsTask(variant, PythonExtension python) {
        def assetDir = variantGenDir(variant, "assets")
        def genTask = project.task(genTaskName(variant, "assets"), type: Copy) {
            doFirst { project.delete(assetDir) }
            from project.configurations.getByName(configName(variant, "targetStdlib"))
            rename { "stdlib.zip" }
            into "$assetDir/$NAME"
        }
        extendMergeTask(variant.getMergeAssets(), genTask)
    }

    void createJniLibsTask(variant, PythonExtension python) {
        def libsDir = variantGenDir(variant, "jniLibs")
        def artifacts = project.configurations.getByName(configName(variant, "targetAbis"))
                        .resolvedConfiguration.resolvedArtifacts
        def genTask = project.task(genTaskName(variant, "jniLibs"), type: Copy) {
            doFirst { project.delete(libsDir) }
            for (art in artifacts) {
                from(project.zipTree(art.file)) { into art.name }
            }
            into libsDir
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