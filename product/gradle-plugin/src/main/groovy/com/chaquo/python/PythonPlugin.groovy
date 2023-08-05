package com.chaquo.python

import com.chaquo.python.internal.*
import org.gradle.api.*
import org.gradle.api.file.*
import org.gradle.api.tasks.*
import org.gradle.process.*
import org.gradle.process.internal.*

class PythonPlugin implements Plugin<Project> {

    Task buildPackagesTask

    public void apply(Project p) {
    }

    void afterEvaluate() {
        buildPackagesTask = createBuildPackagesTask()

        for (variant in (isLibrary ? android.libraryVariants : android.applicationVariants)) {
            def python = new PythonExtension(project)
            python.mergeFrom(android.defaultConfig.python)
            for (flavor in variant.getProductFlavors().reverse()) {
                python.mergeFrom(flavor.python)
            }
        }
    }

    Task createBuildPackagesTask() {
        return project.task("extractPythonBuildPackages") {
            // To avoid the the Windows 260-character limit, make the path as short as
            // possible.
            ext.pythonPath = "$genDir/bp"
            outputs.files(project.fileTree(pythonPath) {
                exclude "**/__pycache__"
            })
            doLast {
                project.delete(pythonPath)
                project.mkdir(pythonPath)
                def zipPath = extractResource("gradle/build-packages.zip", genDir)
                project.copy {
                    from project.zipTree(zipPath)
                    into pythonPath
                }
                project.delete(zipPath)
                project.delete("$genDir/bp.zip")  // From Chaquopy 13.0 and older.
            }
        }
    }

    Task createReqsTask(variant, PythonExtension python) {
        return registerTask("generate", variant, "requirements") {
            def abis = getAbis(variant)
            // Using variantGenDir could cause us to exceed the Windows 260-character filename
            // limit with some packages (e.g. https://github.com/chaquo/chaquopy/issues/164),
            // so use something shorter.
            ext.destinationDir = plugin.buildSubdir("pip", variant)
            dependsOn buildPackagesTask
            inputs.property("abis", abis)
            inputs.property("minApiLevel", variant.mergedFlavor.minSdkVersion.apiLevel)
            inputs.property("buildPython", python.buildPython).optional(true)
            inputs.property("pip", python.pip)
            inputs.property("pyc", python.pyc.pip).optional(true)

            def reqsArgs = []
            for (req in python.pip.reqs) {
                reqsArgs.addAll(["--req", req])
                addReqInput(inputs, req, project.projectDir)
            }
            for (reqFile in python.pip.reqFiles) {
                reqsArgs.addAll(["--req-file", reqFile])
                inputs.files(reqFile)
                try {
                    def file = project.file(reqFile)
                    file.eachLine {
                        // Pip resolves `-r` and `-c` lines  (which we don't currently
                        // detect) relative to the location of the containing requirements
                        // file, while paths to actual requirements are resolved relative
                        // to the working directory
                        // (https://github.com/pypa/pip/pull/4208#issuecomment-429120743).
                        addReqInput(inputs, it, project.projectDir)
                    }
                } catch (FileNotFoundException e) {}
            }

            outputs.dir(destinationDir)
            doLast {
                project.delete(destinationDir)
                project.mkdir(destinationDir)
                if (!reqsArgs.isEmpty()) {
                    execBuildPython(python) {
                        args "-m", "chaquopy.pip_install"
                        args "--target", destinationDir
                        args("--android-abis", *abis)
                        args("--min-api-level", inputs.properties["minApiLevel"])
                        args reqsArgs
                        args "--"
                        args "--disable-pip-version-check"
                        if (!("--index-url" in python.pip.options ||
                              "-i" in python.pip.options)) {
                            // If the user passes --index-url, disable our repository as well
                            // as the default one.
                            args "--extra-index-url", "https://chaquo.com/pypi-7.0"
                            args "--extra-index-url", "https://chaquo.com/pypi-13.1"
                            }
                        args "--implementation", Common.PYTHON_IMPLEMENTATION
                        args "--python-version", pythonVersionInfo(python.version).key
                        args "--abi", (Common.PYTHON_IMPLEMENTATION +
                                       python.version.replace(".", ""))
                        args "--no-compile"
                        args python.pip.options
                    }
                    compilePyc(python, "pip", destinationDir)
                }

                // Requirements subdirectories must exist, or their ZIPs won't be created,
                // and the app will crash (#5631).
                for (subdirName in [Common.ABI_COMMON] + abis) {
                    def subdir = new File("$destinationDir/$subdirName")
                    if (!subdir.exists()) {
                        if (reqsArgs.isEmpty()) {
                            project.mkdir(subdir)
                        } else {
                            throw new GradleException("$subdir was not created: please " +
                                                      "check your buildPython setting")
                        }
                    }
                }
            }
        }
    }

    // This does not currently detect changes to indirect requirements or constraints
    // files (#719).
    void addReqInput(TaskInputs inputs, String req, File baseDir) {
        // # is used for comments, and ; for environment markers.
        req = req.replaceAll(/[#;].*/, "").trim()
        if (req.isEmpty()) return

        File file
        try {
            file = new File(req)
            if (! file.isAbsolute()) {
                // Passing two absolute paths to the File constructor will simply
                // concatenate them rather than returning the second one.
                file = new File(baseDir, req)
            }
            if (! file.exists()) {
                file = null
            }
        } catch (Exception e) {
            // In case any of the above code throws on an invalid filename.
            file = null
        }
        // Do this outside of the try block to avoid hiding exceptions.
        if (file != null) {
            if (file.isDirectory()) {
                inputs.files(project.fileTree(file) {
                    // Ignore any files which may be written while installing.
                    exclude "build", "dist", "**/*.dist-info", "**/*.egg-info"
                    exclude "**/__pycache__"  // See test_pep517_backend_path
                })
            } else {
                inputs.files(file)
            }
        }
    }

    Task createSrcTask(variant, PythonExtension python) {
        // Create the main source set directory if it doesn't already exist, to invite the user
        // to put things in it.
        for (dir in android.sourceSets.main.python.srcDirs) {
            project.mkdir(dir)
        }

        def dirSets = (variant.sourceSets.collect { it.python }
                       .findAll { ! it.sourceFiles.isEmpty() })
        def mergeDir = plugin.buildSubdir("sources", variant)
        return registerTask("merge", variant, "sources") {
            ext.destinationDir = mergeDir
            dependsOn buildPackagesTask
            inputs.property("buildPython", python.buildPython).optional(true)
            inputs.property("pyc", python.pyc.src).optional(true)
            inputs.files(dirSets.collect { it.sourceFiles })
            outputs.dir(destinationDir)
            doLast {
                project.delete(mergeDir)
                project.mkdir(mergeDir)
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
                            def destFile = new File("$mergeDir/$fcd.path")
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

    // We can't remove the .py files here because the static proxy generator needs them.
    // Instead, they'll be excluded when we call makeZip.
    void compilePyc(PythonExtension python, String tag, File dir) {
        Boolean setting = python.pyc[tag]
        if (setting == null || setting) {
            try {
                execBuildPython(python) {
                    args "-m", "chaquopy.pyc"
                    args "--python", python.version
                    args "--quiet"  // TODO #5411: option to display syntax errors
                    if (!setting) {
                        args "--warning"
                    }
                    args dir
                }
            } catch (BuildPythonException e) {
                if (setting) {
                    throw e
                } else {
                    // Messages should be formatted the same as those from chaquopy.pyc.
                    println(
                        "Warning: Failed to compile to .pyc format: ${e.shortMessage}. See " +
                        "https://chaquo.com/chaquopy/doc/current/android.html#android-bytecode.")
                }
            }
        }
    }

    void createProxyTask(variant, PythonExtension python, Task reqsTask, Task srcTask) {
        File destinationDir = plugin.buildSubdir("proxies", variant)
        Task proxyTask = registerTask("generate", variant, "proxies") {
            inputs.files(buildPackagesTask, reqsTask, srcTask)
            inputs.property("buildPython", python.buildPython).optional(true)
            inputs.property("staticProxy", python.staticProxy)
            outputs.dir(destinationDir)
            doLast {
                project.delete(destinationDir)
                project.mkdir(destinationDir)
                if (!python.staticProxy.isEmpty()) {
                    execBuildPython(python) {
                        args "-m", "chaquopy.static_proxy"
                        args "--path", (srcTask.destinationDir.toString() +
                                        File.pathSeparator +
                                        "$reqsTask.destinationDir/common")
                        args "--java", destinationDir
                        args python.staticProxy
                    }
                }
            }
        }
        variant.registerJavaGeneratingTask(proxyTask, destinationDir)
    }

    void execBuildPython(PythonExtension python, Closure closure) {
        if (python.buildPython == null) {
            throw new BuildPythonMissingException("Couldn't find Python")
        }

        ExecResult execResult = null
        try {
            execResult = project.exec {
                environment "PYTHONPATH", buildPackagesTask.pythonPath
                commandLine python.buildPython
                args "-S"  // Avoid interference from site-packages. This is not inherited by
                           // subprocesses, so it's used again in pip_install.py.
                ignoreExitValue true  // A missing executable will still throw an exception.
                closure.delegate = delegate
                closure()
            }
        } catch (ExecException e) {
            throw new BuildPythonInvalidException(e.message)
        }
        try {
            execResult.assertNormalExitValue()
        } catch (ExecException e) {
            throw new BuildPythonFailedException(e.message)
        }
    }
}


class PythonExtension extends BaseExtension {
    Project project
    String version
    String[] buildPython
    Set<String> staticProxy = new TreeSet<>()
    Set<String> extractPackages = new TreeSet<>()
    PipExtension pip = new PipExtension()
    PycExtension pyc = new PycExtension()

    PythonExtension(Project project) {
        this.project = project
    }

    void setDefaults() {
        version = Common.DEFAULT_PYTHON_VERSION
        pip.setDefaults()
        pyc.setDefaults()
    }

    void version(String v) {
        if (v in Common.PYTHON_VERSIONS_SHORT) {
            version = v
            if (v != Common.DEFAULT_PYTHON_VERSION) {
                println("Warning: Python version $v may have fewer packages available. " +
                        "If you experience problems, try switching to version " +
                        "${Common.DEFAULT_PYTHON_VERSION}.")
            }
        } else {
            throw new GradleException("Invalid Python version '$v'. Available versions " +
                                      "are ${Common.PYTHON_VERSIONS_SHORT}.")
        }
    }

    boolean checkBuildPython(bp) {
        try {
            project.exec {
                commandLine bp
                args "--version"
                standardOutput = new ByteArrayOutputStream()
                errorOutput = new ByteArrayOutputStream()
            }
            return true
        } catch (ExecException e) {
            return false
        }
    }

    void buildPython(String... bp) {
        buildPython = bp
        if (!checkBuildPython(bp) && bp.length == 1) {
            // Backward compatibility for when buildPython only took a single string.
            buildPython = bp[0].split(/\s+/)
        }
    }

    String[] getBuildPython() {
        if (buildPython == null) {
            List<List<String>> bps = new ArrayList<>()
            for (suffix in [version, version.split(/\./)[0]]) {
                if (System.getProperty("os.name").startsWith("Windows")) {
                    // See PEP 397. After running the official Windows installer with
                    // default settings, this will be the only Python thing on the PATH.
                    bps.add(["py", "-$suffix"])
                } else {
                    // See PEP 394.
                    bps.add(["python$suffix"])
                }
            }

            // On Windows, both venv and conda create environments containing only a
            // `python` executable, not `python3`, `python3.x`, or `py`. It's also
            // reasonable to use this as a final fallback on Unix (#752).
            bps.add(["python"])

            for (bp in bps) {
                if (checkBuildPython(bp)) {
                    buildPython = bp as String[]
                    break
                }
            }
        }
        return buildPython
    }

    void staticProxy(String... modules)         { staticProxy.addAll(modules) }
    void extractPackages(String... packages)    { extractPackages.addAll(packages) }
    void pip(Closure closure)                   { applyClosure(pip, closure) }
    void pyc(Closure closure)                   { applyClosure(pyc, closure) }

    void mergeFrom(PythonExtension overlay) {
        version = chooseNotNull(overlay.version, this.version)
        buildPython = chooseNotNull(overlay.@buildPython, this.@buildPython)
        staticProxy.addAll(overlay.staticProxy)
        extractPackages.addAll(overlay.extractPackages)
        pip.mergeFrom(overlay.pip)
        pyc.mergeFrom(overlay.pyc)
    }
}


class PipExtension extends BaseExtension {
    List<String> reqs = new ArrayList<>();
    List<String> reqFiles = new ArrayList<>();
    List<String> options = new ArrayList<>();

    void install(String... args) {
        if (args.length == 1) {
            reqs.add(args[0])
        } else if (args.length == 2  &&  args[0].equals("-r")) {
            reqFiles.add(args[1])
        } else {
            throw new GradleException("Invalid python.pip.install format: '" + args.join(" ") + "'")
        }
    }

    // Options are tracked separately from requirements because when installing the second and
    // subsequent ABIs, pip_install uses the same options with a different set of requirements.
    void options (String... args) {
        options.addAll(Arrays.asList(args))
    }

    void mergeFrom(PipExtension overlay) {
        reqs.addAll(overlay.reqs)
        reqFiles.addAll(overlay.reqFiles)
        options.addAll(overlay.options)
    }
}

class BuildPythonException extends GradleException {
    static final String ADVICE = (
        "set buildPython to your Python executable path. See " +
        "https://chaquo.com/chaquopy/doc/current/android.html#buildpython.")
    String shortMessage

    BuildPythonException(String shortMessage, String suffix) {
        super(shortMessage + suffix)
        this.shortMessage = shortMessage
    }
}

// Message will be something like "Couldn't find Python".
class BuildPythonMissingException extends BuildPythonException {
    BuildPythonMissingException(String message) {
        super(message, ". Please either install it, or " + ADVICE)
    }
}

// Message will be something like "Process 'command 'py'' finished with non-zero exit value 1",
// so we need to tell the user how to see the command output.
class BuildPythonFailedException extends BuildPythonException {
    BuildPythonFailedException(String message) {
        super(message,
              "\n\nTo view full details in Android Studio:\n" +
              "* Click the 'Build: failed' caption to the left of this message.\n" +
              "* Then scroll up to see the full output.")
    }
}

// Message will be something like "A problem occurred starting process 'command 'python''".
class BuildPythonInvalidException extends BuildPythonException {
    BuildPythonInvalidException(String message) {
        super(message, ". Please " + ADVICE)
    }
}
