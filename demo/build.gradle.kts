// Top-level build file where you can add configuration options common to all
// sub-projects/modules.
plugins {
    id("com.android.application") version "8.1.3" apply false
    id("org.jetbrains.kotlin.android") version "1.8.10" apply false

    // com.chaquo.python is declared in settings.gradle.kts, because dynamic versions
    // are not possible here. See
    // https://docs.gradle.org/current/userguide/plugins.html#sec:plugin_version_management
}
