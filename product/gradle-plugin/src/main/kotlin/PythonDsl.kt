package com.chaquo.python

import com.chaquo.python.internal.*
import org.gradle.api.*
import org.gradle.api.file.*
import org.gradle.api.model.*
import org.gradle.kotlin.dsl.*
import java.io.Serializable
import javax.inject.*


// TODO inline
private fun <T: Any?> chooseNotNull(overlay: T, base: T) =
    overlay ?: base


// `Serializable` allows the extension to be used as a task input property.
abstract class BaseExtension : Serializable {
    // If a setting's default value is not null or empty, we can't just set it in a
    // field initializer, because then a value explicitly set by the user in
    // defaultConfig could be overridden by a default value from a product flavor.
    // Instead, such values are set in this method, which is only called on
    // defaultConfig.
    internal open fun setDefaults() {}
}


// All DSL classes must be instantiated via one of Gradle's "decorating" API such as
// ObjectFactory.newInstance. Otherwise, when Groovy calls the Action methods, it will
// use the wrong delegate.
abstract class ChaquopyExtension @Inject constructor(objects: ObjectFactory) {
    val defaultConfig = objects.newInstance<PythonExtension>("defaultConfig").apply {
        setDefaults()
    }
    fun defaultConfig(action: Action<PythonExtension>) = action.execute(defaultConfig)

    val productFlavors = objects.domainObjectContainer(PythonExtension::class)
    fun productFlavors(action: Action<NamedDomainObjectContainer<PythonExtension>>) =
        action.execute(productFlavors)

    val sourceSets = objects.domainObjectContainer(SourceDirectorySet::class) { name ->
        objects.sourceDirectorySet(name, name).apply {
            srcDir("src/$name/python")
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

    val pyc = objects.newInstance<PycExtension>()
    fun pyc(action: Action<PycExtension>) = action.execute(pyc)

    override fun setDefaults() {
        version = Common.DEFAULT_PYTHON_VERSION
        pyc.setDefaults()
    }

    internal fun mergeFrom(overlay: PythonExtension) {
        _version = overlay.version ?: version
        pyc.mergeFrom(overlay.pyc)
    }
}


abstract class PycExtension() : BaseExtension() {
    var src: Boolean? = null
    var pip: Boolean? = null
    var stdlib: Boolean? = null

    override fun setDefaults() {
        stdlib = true
    }

    internal fun mergeFrom(overlay: PycExtension) {
        src = chooseNotNull(overlay.src, src)
        pip = chooseNotNull(overlay.pip, pip)
        stdlib = chooseNotNull(overlay.stdlib, stdlib)
    }
}