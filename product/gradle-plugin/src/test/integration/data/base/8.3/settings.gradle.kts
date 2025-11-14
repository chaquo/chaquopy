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
