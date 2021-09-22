# Introduction

This file contains instructions for building and testing Chaquopy. These instructions have been
tested on Linux x86-64, and Windows x86-64 with MSYS2. However, the resulting packages can be
used on any supported Android build platform (Windows, Linux or Mac).

Alternatively, you might want to use the automated Docker-based build process: see
`../README.md`.


# Build prerequisites

* JDK versions 8 and 11. Version 8 is used for the runtime tests (see javaHome in
  product/runtime/build.gradle), while the integration tests use whichever version was bundled
  with the corresponding version of Android Studio: 4.1 and older use version 8, while 4.2 and
  newer use version 11.
* Python requirements in `runtime/requirements-build.txt`.
* Android SDK, including the following packages:
   * CMake: see `Dockerfile` for version number.
   * NDK (side by side): see `target/Dockerfile` for version number.
   * SDK Platform corresponding to `COMPILE_SDK_VERSION` in
     `product/buildSrc/src/main/java/com/chaquo/python/Common.java`.
* Android sysroots in `../target/toolchains/<abi>/sysroot`. Either generate them using the
  commands in `../build-maven.sh`, or copy them from another machine. For this purpose, you
  only need to copy the Python headers in `usr/include/pythonX.Y` and the library
  `usr/lib/libpythonX.Y.so`.

Create a `local.properties` file in `product` (i.e. the same directory as this README), with
the following content:

    sdk.dir=<Android SDK directory>
    ndk.dir=<Android SDK directory>/ndk/<version>
    chaquopy.java.home.8=<path>
    chaquopy.java.home.11=<path>

If building with a non-standard license mode, also add the line:

    chaquopy.license_mode=<mode>

Current modes are `free` for no license enforcement at all, and `ec` for Electron Cash.


# Build

The build can be done either at the command line using `gradlew`, or by opening the project in
Android Studio or IntelliJ.

The top-level Gradle tasks are as follows. All artifacts are generated in the `maven` directory
in the repository root. All apps in this repository are set to build against that local Maven
repository, not the one on chaquo.com.

* `gradle-plugin:publish` for the `com.chaquo.python:gradle` artifact.
* `runtime:publish` for the `com.chaquo.python.runtime` artifacts. For a release build, add `-P
  cmakeBuildType=Release` to the Gradle command line.


# Runtime tests

Most of the runtime library unit tests included in the [Android demo
app](https://github.com/chaquo/chaquopy/) can also be run locally. You must have installed the
same major.minor version of Python as Chaquopy currently uses: this is represented below as
`X.Y`.

Linux prerequisites:

* Python development headers (e.g. `pythonX.Y-dev` on Debian)

Windows prerequisites:

* Install MSYS2.
* Add the following line to `local.properties`: `mingw.dir=C\:/msys64/mingw64`
* Make sure the `mingw64\bin` directory is on the `PATH`, and is the directory actually used
  for invocations of `pythonX.Y`.

Common prerequisities (on Windows, these must be the MSYS2 versions):

* GCC and binutils.
* The same Python major.minor version as Chaquopy currently uses.
  * On Linux, if your distribution supplies a different Python version, it's easy to build the
    correct version from source.
  * On Windows, if MSYS2 has already moved on to the next Python version, download the correct
    version from http://repo.msys2.org/mingw/mingw64/ and install it with `pacman -U`.

The tests are run by the Gradle tasks `runtime:testPython` and `runtime:testJava`. Or run
`runtime:check` to test everything at once.


# Gradle plugin tests

There are a few Gradle plugin unit tests, which can be run with the Gradle task
`gradle-plugin:testPython`.

However, most of the Gradle plugin functionality is covered by the integration tests.
Prerequisites:

* The test script requires the packages listed in
  `gradle-plugin/src/test/integration/requirements.txt`. It does not currently work in a
  virtualenv, so use `pip install --user` instead, making sure that you run pip with the same
  major.minor Python version as Chaquopy currently uses.
* On Windows, integration tests are not run with the MSYS2 Python, but rather with the `py`
  launcher (PEP 397). This is installed by default by the official Windows releases from
  python.com.

The integration tests are run by the Gradle task `gradle-plugin:testIntegration-X.Y`, where
`X.Y` is the Android Gradle plugin version to test against (e.g. `7.0`).

For Android Gradle plugin versions 3.6 and 4.0, you must install the matching NDK version
listed [here](https://developer.android.com/studio/projects/configure-agp-ndk).

The full set of tests will take a long time. To run only some of them, add `-P
testPythonArgs=<args>` to the Gradle command line, where `<args>` is a space-separated list of
test classes or methods (e.g. `test_gradle_plugin.Basic.test_variant`). Other [unittest command
line options](https://docs.python.org/3/library/unittest.html#command-line-interface) can also
be given here.
