pluginManagement {
    // These are defined in gradle.properties.
    val chaquopyRepository: String by settings
    val chaquopyVersion: String by settings
    val agpVersion: String by settings

    repositories {
        maven { url = uri(chaquopyRepository) }
        google {
            content {
                includeGroupByRegex("com\\.android.*")
                includeGroupByRegex("com\\.google.*")
                includeGroupByRegex("androidx.*")
            }
        }
        mavenCentral()
        gradlePluginPortal()
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
    for (ext in listOf("gradle", "gradle.kts")) {
        if (File(f, "build.$ext").exists()) {
            include(f.name)
            break
        }
    }
}
