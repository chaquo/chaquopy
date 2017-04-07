package com.chaquo.python

import org.gradle.api.*
import org.gradle.api.plugins.ExtensionAware

// FIXME unit test everything
class PythonPlugin implements Plugin<Project> {
    public static final String NAME = "python"

    def android
    File genDir, intDir

    void apply(Project project) {
        android = project.android

        extend(android.defaultConfig)
        android.productFlavors.whenObjectAdded { extend(it) }
        // I also tried adding it to buildTypes but it had no effect for some reason

        // TODO add "python" source set property

        project.afterEvaluate { afterEvaluate(it) }
    }

    void extend(ExtensionAware ea) {
        ea.extensions.create(NAME, PythonExtension)
    }

    void afterEvaluate(Project project) {
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

            genDir = new File(project.buildDir, "generated")
            intDir = new File(project.buildDir, "intermediates")
            createAssetTask(project, variant, python);
            // TODO native libs
            // TODO Java lib (maybe better to generate Gradle dependency so it's on
            // the classpath for interactive editing)
            // TODO Java generated source

        }
    }

    void createAssetTask(Project project, variant, PythonExtension python) {
        File genAssetDir = new File(genDir, "assets/python/$variant.dirName")

        // TODO download Python and packages to non-variant-specific cache in generated/python

        Task genTask = project.task("generatePython${variant.name.capitalize()}Assets") {
            outputs.dir genAssetDir
            doLast {
                project.delete(genAssetDir)
                project.mkdir(genAssetDir)
                def pw = new PrintWriter(new File(genAssetDir, "asset.txt"))
                pw.println("Hello asset")
                pw.close()
            }
        }

        Task mergeTask = variant.getMergeAssets()
        mergeTask.dependsOn(genTask)
        mergeTask.inputs.dir(genAssetDir)
        mergeTask.doLast {
            project.copy {
                from genAssetDir
                into mergeTask.outputDir
            }
        }
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