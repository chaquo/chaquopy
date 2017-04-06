package com.chaquo.python

import org.gradle.api.*
import org.gradle.api.plugins.ExtensionAware

// FIXME unit test everything
class PythonPlugin implements Plugin<Project> {
    def android

    void apply(Project project) {
        android = project.android

        extend(android.defaultConfig)
        android.productFlavors.whenObjectAdded { extend(it) }
        // I also tried adding it to buildTypes but it had no effect for some reason

        // FIXME add "python" source set property

        project.afterEvaluate { afterEvaluate(it) }
    }

    void extend(ExtensionAware ea) {
        ea.extensions.create(PythonExtension.NAME, PythonExtension)
    }

    public void afterEvaluate(Project project) {
        for (variant in android.applicationVariants) {
            PythonExtension pe = new PythonExtension()

            pe.mergeFrom(android.defaultConfig)
            for (flavor in variant.getProductFlavors().reverse()) {
                pe.mergeFrom(flavor)
            }

            if (pe.version == null) {
                throw new IllegalStateException("No Python version defined for variant $variant.name")
            }
        }

        // FIXME assets (stdlib, requirements, app code)
        // FIXME native libs
        // FIXME Java lib
        // FIXME Java source
    }
}


class PythonExtension {
    public static final String NAME = "python"

    String version

    void mergeFrom(Object o) {
        PythonExtension overlay = o.python
        version = chooseNotNull(overlay.version, version);
    }

    private static <T> T chooseNotNull(T overlay, T base) {
        return overlay != null ? overlay : base
    }

}