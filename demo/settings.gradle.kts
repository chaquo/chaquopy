pluginManagement {
    repositories {
        maven { url = uri("../maven") }
        google()
        mavenCentral()
        gradlePluginPortal()
    }
    plugins {
        id("com.chaquo.python") version file("../VERSION.txt").readText().trim()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}
include(":app")
