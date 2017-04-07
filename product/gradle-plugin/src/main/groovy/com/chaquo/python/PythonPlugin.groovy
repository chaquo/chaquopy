package com.chaquo.python

import org.gradle.api.*
import org.gradle.api.plugins.*
import org.gradle.api.tasks.*

// FIXME unit test everything
class PythonPlugin implements Plugin<Project> {
    public static final String NAME = "python"

    Project project
    def android

    void apply(Project project) {
        this.project = project
        android = project.android

        extend(android.defaultConfig)
        android.productFlavors.whenObjectAdded { extend(it) }
        // I also tried adding it to buildTypes but it had no effect for some reason

        // TODO add "python" source set property

        project.afterEvaluate { afterEvaluate() }
    }

    void extend(ExtensionAware ea) {
        ea.extensions.create(NAME, PythonExtension)
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

            createAssetTask(variant, python);
            createNativeLibsTask(variant, python)
            // TODO Java lib (maybe better to generate Gradle dependency so it's on
            // the classpath for interactive editing)
            // TODO Java generated source

        }
    }

    void createAssetTask(variant, PythonExtension python) {
        File assetDir = genVariantDir(variant, "assets")
        Task genTask = project.task("generatePython${variant.name.capitalize()}Assets",
                                    type: Copy) {
            doFirst {
                project.delete(assetDir)
            }
            from project.file("${targetDir(python)}/stdlib.zip", PathValidation.FILE)
            into assetDir
        }
        extendMergeTask(variant.getMergeAssets(), genTask, genTask.outputs)
    }

    void createNativeLibsTask(variant, PythonExtension python) {
        for (mergeTask in
             project.getTasksByName("merge${variant.name.capitalize()}JniLibFolders", false)) {
            // TODO use ABI filters
            extendMergeTask(mergeTask, null,
                            project.file("${targetDir(python)}/lib", PathValidation.DIRECTORY))
        }
    }

    void extendMergeTask(Task mergeTask, depTasks, files) {
        if (depTasks) {
            mergeTask.dependsOn(depTasks)
        }
        if (files) {
            mergeTask.inputs.files(files)
            mergeTask.doLast {
                project.copy {
                    from files
                    into mergeTask.outputDir
                }
            }
        }
    }

    private File genDir() {
        return new File(project.buildDir, "generated/${NAME}")
    }

    File targetDir(PythonExtension python) {
        return new File(genDir(), "target/$python.version")
    }

    private File genVariantDir(variant, String type) {
        return new File(genDir(), "$type/$variant.dirName")
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