package com.chaquo.python

import com.chaquo.python.internal.*
import org.gradle.api.*
import org.gradle.api.file.*
import org.gradle.kotlin.dsl.*
import java.io.Serializable


// TODO inline
private fun <T: Any?> chooseNotNull(overlay: T, base: T) =
    overlay ?: base


open class BaseExtension : Serializable {
    // If a setting's default value is not null or empty, we can't just set it in a
    // field initializer, because then a value explicitly set by the user in
    // defaultConfig could be overridden by a default value from a product flavor.
    // Instead, such values are set in this method, which is only called on
    // defaultConfig.
    internal open fun setDefaults() {}

}




open class ChaquopyExtension(project: Project) {
    val defaultConfig = PythonExtension(project, "defaultConfig").apply {
        setDefaults()
    }
    val productFlavors =
        project.objects.domainObjectContainer(PythonExtension::class) { name ->
            PythonExtension(project, name)
        }
    val sourceSets =
        project.objects.domainObjectContainer(SourceDirectorySet::class) { name ->
            project.objects.sourceDirectorySet(name, name).apply {
                srcDir("src/$name/python")
            }
        }
}


class PythonExtension(project: Project, val name: String) : BaseExtension() {
    val version = Common.DEFAULT_PYTHON_VERSION
    val pyc = PycExtension()

    override fun setDefaults() {
        pyc.setDefaults()
    }
}

class PycExtension : BaseExtension() {
    var src: Boolean? = null
    var pip: Boolean? = null
    var stdlib: Boolean? = null

    override fun setDefaults() {
        stdlib = true
    }

    // Old DSL
    fun src(value: Boolean) { src = value }
    fun pip(value: Boolean) { pip = value }
    fun stdlib(value: Boolean) { stdlib = value }

    internal fun mergeFrom(overlay: PycExtension) {
        src = chooseNotNull(overlay.src, src)
        pip = chooseNotNull(overlay.pip, pip)
        stdlib = chooseNotNull(overlay.stdlib, stdlib)
    }
}