package com.chaquo.python

import org.gradle.api.*
import org.gradle.api.plugins.ExtensionAware

class PythonPlugin implements Plugin<Project> {
    void apply(Project project) {
        def android = project.android
        extend(android.defaultConfig)
        for (container in [android.productFlavors, android.buildTypes]) {
            container.whenObjectAdded { flavor -> extend(flavor) }
        }

        project.afterEvaluate {

        }
    }

    void extend(ExtensionAware ea) {
        ea.extensions.create("python", PythonExtension)
    }
}


class PythonExtension {
    String foo
}