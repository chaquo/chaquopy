pluginManagement {
    // These are defined in gradle.properties.
    val chaquopyRepository: String by settings
    val chaquopyVersion: String by settings
    val agpVersion: String by settings
    val kotlinVersion: String by settings

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
        id("com.chaquo.python") version chaquopyVersion
    }
}

plugins {
    id("com.android.application") apply false
    id("com.android.library") apply false
    id("com.android.dynamic-feature") apply false
    id("com.chaquo.python") apply false
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
