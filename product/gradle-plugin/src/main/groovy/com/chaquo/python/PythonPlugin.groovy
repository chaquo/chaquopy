package com.chaquo.python

import org.gradle.api.*
import org.gradle.api.file.*

class PythonPlugin implements Plugin<Project> {
    public void apply(Project p) {
    }

    void createProxyTask(variant, PythonExtension python, Task reqsTask, Task srcTask) {
        File outputDir = plugin.buildSubdir("proxies", variant)
        Task proxyTask = registerTask("generate", variant, "proxies") {
            inputs.files(buildPackagesTask, reqsTask, srcTask)
            inputs.property("buildPython", python.buildPython).optional(true)
            inputs.property("staticProxy", python.staticProxy)
            doLast {
                if (!python.staticProxy.isEmpty()) {
                    execBuildPython {
                        args "-m", "chaquopy.static_proxy"
                        args "--path", (srcTask.outputDir.toString() +
                                        File.pathSeparator +
                                        "${reqsTask.outputDir}/common")
                        args "--java", outputDir
                        args python.staticProxy
                    }
                }
            }
        }
        variant.registerJavaGeneratingTask(proxyTask, outputDir)
    }
}


class PythonExtension extends BaseExtension {
    Set<String> staticProxy = new TreeSet<>()
    Set<String> extractPackages = new TreeSet<>()

    void staticProxy(String... modules)         { staticProxy.addAll(modules) }
    void extractPackages(String... packages)    { extractPackages.addAll(packages) }

    void mergeFrom(PythonExtension overlay) {
        staticProxy.addAll(overlay.staticProxy)
        extractPackages.addAll(overlay.extractPackages)
    }
}
