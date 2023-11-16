import com.chaquo.python.internal.BuildCommon
import com.chaquo.python.internal.Common
import com.chaquo.python.internal.Common.findExecutable
import com.chaquo.python.internal.Common.osName

plugins {
    `java-gradle-plugin`
    `kotlin-dsl`
}

group = "com.chaquo.python"

gradlePlugin {
    plugins {
        create("gradle") {
            id = "com.chaquo.python"
            implementationClass = "com.chaquo.python.PythonPlugin"

            // For these fields, the `pom` block in the root build.gradle doesn't have
            // any effect on the plugin marker artifact.
            displayName = "Chaquopy"
            description = "The Python SDK for Android"
        }
    }
}

dependencies {
    // gradleApi() (for the API of Gradle itself) is added automatically by
    // java-gradle-plugin.
    //
    // gradle-api is the API of the Android Gradle plugin. If we made it an
    // `implementation` dependency, and the user selected an AGP version that was too
    // old, then Gradle would use the MIN_AGP_VERSION of gradle-api along with the
    // older version of the AGP, and the build would fail with an incomprehensible
    // error message before even getting as far as our own AGP version check.
    compileOnly("com.android.tools.build:gradle-api:${Common.MIN_AGP_VERSION}")

    implementation("org.apache.commons:commons-compress:1.18")
    implementation("org.json:json:20160810")
}

java {
    sourceCompatibility = JavaVersion.VERSION_1_8
}

sourceSets.main {
    java.srcDir("../buildSrc/src/main/java")
}

tasks.register<Zip>("zipBuildPackages") {
    destinationDirectory.set(file("$buildDir/tmp/$name"))
    archiveFileName.set("build-packages.zip")
    from("src/main/python")
    exclude("**/*.pyc")
}

tasks.processResources {
    doFirst { delete(destinationDir) }
    into("com/chaquo/python/gradle") {
        from(tasks.named("zipBuildPackages"))
    }
}

// We don't use the Exec task because on Windows, it causes the integration tests to
// hang if they spawn a Gradle daemon, because their stdout is inherited by the daemon
// and will therefore never close (https://github.com/gradle/gradle/issues/3987). For
// example, if you pass Exec the command `cmd /c start notepad.exe`, then cmd will exit
// immediately, but the Exec task won't complete until you close Notepad.
abstract class TestPythonTask : DefaultTask() {
    lateinit var pythonVersion: String

    // Emulate the necessary Exec properties.
    lateinit var workingDir: String
    val environment: MutableMap<String, String> = HashMap()

    init {
        group = "verification"
    }

    @TaskAction
    fun run() {
        val pb = ProcessBuilder()
        val command = pb.command()
        pb.directory(File(workingDir))
        pb.environment().putAll(environment)

        command += if (osName() == "windows") {
            listOf(findExecutable("py"), "-$pythonVersion")
        } else {
            listOf(findExecutable("python$pythonVersion"))
        }
        command += listOf("-m", "unittest")
        val args = project.findProperty("testPythonArgs")
        if (args != null) {
            command += "-v"
            command += args.toString().split(Regex("""\s+""")).filter { !it.isEmpty() }
        } else {
            command += listOf("discover", "-v")
        }
        pb.command(command)

        // Lower levels mean more logging.
        if (project.gradle.startParameter.logLevel <= LogLevel.INFO) {
            println("TestPythonTask: $command")
        }

        pb.redirectErrorStream(true)  // Merge stdout and stderr.
        val process = pb.start()

        // pb.inheritIO() doesn't seem to prevent stdout from blocking. Even if it
        // did, the output would be lost because it would inherit the Gradle
        // daemon's *native* stdout, which isn't connected to anything. So we
        // capture the output manually and send it to System.out, which is connected
        // to the Gradle client.
        val stdout = process.inputStream  // It's an input from our point of view.
        val buffer = ByteArray(1024 * 1024)
        while (true) {
            val available = stdout.available()
            if (available > 0) {
                val len = stdout.read(buffer, 0, Math.min(available, buffer.size))
                System.out.write(buffer, 0, len)
                System.out.flush()
            } else if (process.isAlive()) {
                Thread.sleep(100)
            } else {
                break
            }
        }
        val status = process.waitFor()
        if (status != 0) {
            throw GradleException("Exit status $status")
        }
    }
}

tasks.register<TestPythonTask>("testPython") {
    pythonVersion = "3.7"  // Minimum supported buildPython version
    workingDir = "$projectDir/src/test/python"
}

tasks.register("testIntegration") {
    group = "verification"
}

tasks.check {
    dependsOn("testPython", "testIntegration")
}

// This should match the version discovery logic in ci.yml.
val INTEGRATION_DIR = "$projectDir/src/test/integration"
for (f in file("$INTEGRATION_DIR/data/base").listFiles()!!) {
    val version = f.name
    if (version.contains(".")) {
        val task = tasks.register<TestPythonTask>("testIntegration-$version") {
            pythonVersion = Common.DEFAULT_PYTHON_VERSION
            if (System.getenv("CHAQUOPY_NO_BUILD") == null) {  // Used in CI
                dependsOn(tasks.publish, ":runtime:publish")
            }
            workingDir = INTEGRATION_DIR
            environment["CHAQUOPY_AGP_VERSION"] = version
            environment["ANDROID_HOME"] = BuildCommon.androidHome(project)
        }
        tasks.named("testIntegration") { dependsOn(task) }
    }
}
