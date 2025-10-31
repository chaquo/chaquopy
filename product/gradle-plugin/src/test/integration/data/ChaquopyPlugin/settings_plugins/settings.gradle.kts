pluginManagement {
    repositories {
        maven { url = uri("""{{ chaquopyRepository }}""") }
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
}

plugins {
    id("com.android.application") version "{{ agpVersion }}" apply false
    id("com.android.library") version "{{ agpVersion }}" apply false
    id("com.android.dynamic-feature") version "{{ agpVersion }}" apply false
    id("com.chaquo.python") version "{{ chaquopyVersion }}" apply false
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
