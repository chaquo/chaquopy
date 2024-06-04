// Top-level build file where you can add configuration options common to all sub-projects/modules.
plugins {
    // Plugin versions are configured in settings.gradle.kts, because dynamic versions
    // are not possible here. See
    // https://docs.gradle.org/current/userguide/plugins.html#sec:plugin_version_management
    //
    // Listing the plugins in settings.gradle.kts is enough to enable the `plugins`
    // syntax in subprojects, but the `apply` syntax requires them to be listed here as
    // well.
    id("com.android.application") apply false
    id("com.android.library") apply false
    id("com.android.dynamic-feature") apply false
    id("org.jetbrains.kotlin.android") apply false
    id("com.chaquo.python") apply false
}
