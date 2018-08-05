# Introduction

This file contains instructions for building and testing Chaquopy. These instructions have been
tested on Linux x86-64, and Windows x86-64 with MSYS2. However, the resulting packages can be
used on any supported Android build platform (Windows, Linux or Mac).


# Build prerequisites

* JDK 8 or later with the environment variable `JAVA_HOME` set to its location.
* Python requirements in `runtime/requirements-build.txt`.
* Android SDK, including the following packages (names for the command-line `sdkmanager` are in
  parentheses).
   * CMake (`cmake;3.6.4111459`)
   * NDK (`ndk-bundle`)
   * SDK Platform corresponding to `COMPILE_SDK_VERSION` in
     `product/buildSrc/src/main/java/com/chaquo/python/Common.java` (e.g.
     `platforms;android-21`).
* Crystax NDK 10.3.2.
* Crystax libraries and includes for each Python version. These should be in `sources/python`
  within the Crystax directory: either generate them using the instructions in
  `target/README.md`, or copy them from another machine.

Create a `local.properties` file in `product` (i.e. the same directory as this README), with
the following content:

    sdk.dir=<Android SDK directory>
    ndk.dir=<Android SDK directory>/ndk-bundle
    crystax.dir=<Crystax NDK directory>

If building with a non-standard license mode, also add the line:

    chaquopy.license_mode=<mode>

Current modes are `free` for no license enforcement at all, and `ec` for Electron Cash.


# Build

The build can be done either at the command line using `gradlew`, or by opening the project in
Android Studio or IntelliJ.

Run the Gradle task `gradle-plugin:assemble`. (For a release build, add `-P
cmakeBuildType=Release` to the Gradle command line.) The resulting JAR file will be generated
in `product/gradle-plugin/build/libs`.

To generate the POM file for the Maven repository, run the Gradle task
`gradle-plugin:writePom`.


# Runtime tests

Most of the runtime library unit tests included in the [Android demo
app](https://github.com/chaquo/chaquopy/) can also be run locally.

Linux prerequisites:

* Python development headers (e.g. `python3.6-dev` on Debian)

Windows prerequisites:

* Install MSYS2.
* Add the following line to `local.properties`: `mingw.dir=C\:/msys64/mingw64`
* Make sure the `mingw64\bin` directory is on the `PATH`, and is the directory actually used
  for invocations of `pythonX.Y`.

Common prerequisities (on Windows, these must be the MSYS2 versions):

* GCC and binutils.
* Python of the same major.minor version as you are testing.

The tests are run by the Gradle tasks `runtime:testPython-X.Y` and `runtime:testJava-X.Y`,
where `X.Y` is the Python version (e.g. 3.6). Or run `runtime:check` to test everything at
once.


# Gradle plugin tests

There are a few Gradle plugin unit tests, which can be run with the Gradle task
`gradle-plugin:testPython-X`, where `X` is the Python major version (e.g. 3).

However, most of the Gradle plugin functionality is covered by the integration tests.
Prerequisites:

* The test script requires Python 3.6, and the requirements in
  `gradle-plugin/src/test/integration/requirements.txt`. It does not currently work in a
  virtualenv, so use `pip install --user` instead, making sure that you run the pip for Python
  3.6.
* On Windows, integration tests are not run with the MSYS2 Python, but rather with the `py`
  launcher (PEP 397). This is installed by default by the official Windows releases from
  python.com.

The tests are run by the Gradle task `gradle-plugin:testIntegration-X.Y`, where `X.Y` is the
Android Studio version to test against (e.g. 3.1). The full set of tests will take a long time.
To run only some of them, add `-P testPythonArgs=<args>` to the Gradle command line, where
`<args>` is a space-separated list of test classes or methods (e.g.
`test_gradle_plugin.Basic.test_variant`). Other [unittest command line
options](https://docs.python.org/3/library/unittest.html#command-line-interface) can also be
given here.
