pluginManagement {
    // These are defined in gradle.properties.
    val chaquopyRepository: String by settings
    val chaquopyVersion: String by settings
    val agpVersion: String by settings

    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
        maven { url = uri(chaquopyRepository) }
    }
    plugins {
        id("com.android.application") version agpVersion
        id("com.android.library") version agpVersion
        id("com.android.dynamic-feature") version agpVersion
        id("org.jetbrains.kotlin.android") version "1.9.0"
        id("com.chaquo.python") version chaquopyVersion
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "My Application"

for (f in rootDir.listFiles()!!) {
    if (f.isDirectory) {
        for (buildGradle in listOf("build.gradle", "build.gradle.kts")) {
            if (File(f, buildGradle).exists()) {
                include(f.name)
            }
        }
    }
}
