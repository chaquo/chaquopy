package com.chaquo.python

import org.gradle.api.*
import org.gradle.api.file.*

class PythonPlugin implements Plugin<Project> {
    public void apply(Project p) {
    }

    Task createSrcTask(variant, PythonExtension python) {
        // Create the main source set directory if it doesn't already exist, to invite
        // the user to put things in it.
        for (dir in android.sourceSets.main.python.srcDirs) {
            project.mkdir(dir)
        }

        return registerTask("merge", variant, "sources") {
            inputs.files(buildPackagesTask)
            inputs.property("buildPython", python.buildPython).optional(true)
            inputs.property("pyc", python.pyc.src).optional(true)

            def dirSets = (variant.sourceSets.collect { it.python }
                    .findAll { ! it.sourceFiles.isEmpty() })
            inputs.files(dirSets.collect { it.sourceFiles })

            outputDir = plugin.buildSubdir("sources", variant)
            doLast {
                project.copy {
                    into mergeDir
                    exclude "**/*.pyc", "**/*.pyo"
                    exclude "**/*.egg-info"  // See ExtractPackages.test_change.
                    duplicatesStrategy "fail"
                    for (dirSet in dirSets) {
                        for (File srcDir in dirSet.srcDirs) {
                            from(srcDir) {
                                excludes = dirSet.filter.excludes
                                includes = dirSet.filter.includes
                            }
                        }
                    }
                    // Allow duplicates for empty files (e.g. __init__.py)
                    eachFile { FileCopyDetails fcd ->
                        if (fcd.file.length() == 0) {
                            def destFile = new File("$mergeDir/${fcd.path}")
                            if (destFile.exists() && destFile.length() == 0) {
                                fcd.duplicatesStrategy = DuplicatesStrategy.INCLUDE
                            }
                        }
                    }
                }
                compilePyc(python, "src", mergeDir)
            }
        }
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
