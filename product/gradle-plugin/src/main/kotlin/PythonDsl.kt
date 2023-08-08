package com.chaquo.python

import com.chaquo.python.internal.*
import org.gradle.api.*
import org.gradle.api.file.*
import org.gradle.api.model.*
import org.gradle.kotlin.dsl.*
import java.io.*
import java.util.*
import javax.inject.*


// `Serializable` allows the extension to be used as a task input property.
abstract class BaseExtension : Serializable {
    // If a setting's default value is not null or empty, we can't just set it in a
    // field initializer, because then a value explicitly set by the user in
    // defaultConfig could be overridden by a default value from a product flavor.
    // Instead, default values are set in this method, which is only called on
    // defaultConfig.
    internal open fun setDefaults() {}
}


// All DSL classes must be instantiated via one of Gradle's "decorating" API such as
// ObjectFactory.newInstance. Otherwise, when Groovy calls the Action methods, it will
// use the wrong delegate.
abstract class ChaquopyExtension @Inject constructor(
    objects: ObjectFactory, layout: ProjectLayout
) {
    val defaultConfig = objects.newInstance<PythonExtension>("defaultConfig").apply {
        setDefaults()
    }
    fun defaultConfig(action: Action<PythonExtension>) = action.execute(defaultConfig)

    val productFlavors = objects.domainObjectContainer(PythonExtension::class)
    fun productFlavors(action: Action<NamedDomainObjectContainer<PythonExtension>>) =
        action.execute(productFlavors)

    val sourceSets = objects.domainObjectContainer(SourceDirectorySet::class) { name ->
        objects.sourceDirectorySet(name, name).apply {
            val path = File(layout.projectDirectory.asFile, "src/$name/python")
            srcDir(path)

            // Create the main source directory automatically, to invite the user to put
            // things in it.
            if (name == "main") {
                path.mkdir()
            }
        }
    }
    fun sourceSets(action: Action<NamedDomainObjectContainer<SourceDirectorySet>>) =
        action.execute(sourceSets)
}


// According to ObjectFactory.domainObjectContainer, "the specified element type must
// have a public constructor which takes the name as a String parameter", and "all
// objects MUST expose their name as a bean property called 'name'."
abstract class PythonExtension @Inject constructor (
    val name: String, objects: ObjectFactory
) : BaseExtension() {
    private var _version: String? = null

    var version: String?
        get() = _version
        set(value) {
            if (value !in Common.PYTHON_VERSIONS_SHORT) {
                throw GradleException(
                    "Invalid Python version '$value'. Available versions are " +
                    "${Common.PYTHON_VERSIONS_SHORT}.")
            }
            if (value != Common.DEFAULT_PYTHON_VERSION) {
                println("Warning: Python version $value may have fewer packages " +
                "available. If you experience problems, try switching to " +
                "version ${Common.DEFAULT_PYTHON_VERSION}.")
            }
            _version = value
        }

    var buildPython: List<String>? = null
    fun buildPython(vararg bp: String) { buildPython = bp.asList() }

    val extractPackages = TreeSet<String>()
    fun extractPackages(vararg modules: String) { extractPackages += modules }

    val staticProxy = TreeSet<String>()
    fun staticProxy(vararg modules: String) { staticProxy += modules }

    val pip = objects.newInstance<PipExtension>()
    fun pip(action: Action<PipExtension>) = action.execute(pip)

    val pyc = objects.newInstance<PycExtension>()
    fun pyc(action: Action<PycExtension>) = action.execute(pyc)

    override fun setDefaults() {
        version = Common.DEFAULT_PYTHON_VERSION
        pip.setDefaults()
        pyc.setDefaults()
    }

    internal fun mergeFrom(overlay: PythonExtension) {
        // Bypass setter to avoid repeated warnings.
        _version = overlay.version ?: version

        buildPython = overlay.buildPython ?: buildPython
        extractPackages += overlay.extractPackages
        staticProxy += overlay.staticProxy
        pip.mergeFrom(overlay.pip)
        pyc.mergeFrom(overlay.pyc)
    }
}


abstract class PipExtension : BaseExtension() {
    internal val reqs = ArrayList<String>()
    internal val reqFiles = ArrayList<String>()
    internal val options = ArrayList<String>()

    fun install(vararg args: String) {
        if (args.size == 1) {
            reqs += args[0]
        } else if (args.size == 2 && args[0] == "-r") {
            reqFiles += args[1]
        } else {
            throw GradleException("Invalid pip install format: ${args.asList()}")
        }
    }

    // Options are tracked separately from requirements because when installing the
    // second and subsequent ABIs, pip_install uses the same options with a different
    // set of requirements.
    fun options(vararg args: String) {
        options += args
    }

    internal fun mergeFrom(overlay: PipExtension) {
        reqs += overlay.reqs
        reqFiles += overlay.reqFiles
        options += overlay.options
    }
}


abstract class PycExtension() : BaseExtension() {
    var src: Boolean? = null
    var pip: Boolean? = null
    var stdlib: Boolean? = null

    internal fun mergeFrom(overlay: PycExtension) {
        src = overlay.src ?: src
        pip = overlay.pip ?: pip
        stdlib = overlay.stdlib ?: stdlib
    }
}
