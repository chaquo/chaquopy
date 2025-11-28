pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
        maven { url = uri("""{{ chaquopyRepository }}""") }
    }}

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
