**NOTE: The BeeWare project is currently using this branch as an interim measure
for building binary wheels for iOS, tvOS and watchOS. For that purpose, most of
this repository can be ignored, as it is Android specific; the `server/pypi` folder
contains the parts that are interesting for the purposes of iOS etc.**

# Chaquopy: the Python SDK for Android

Chaquopy provides everything you need to include Python components in an Android app,
including:

* Full integration with Android Studio's standard Gradle build system.
* Simple APIs for calling Python code from Java/Kotlin, and vice versa.
* A wide range of third-party Python packages, including SciPy, OpenCV, TensorFlow and many
  more.

To get started, see the [documentation](https://chaquo.com/chaquopy/doc/current/).


## Repository layout

This repository contains the following components:

* `product` contains Chaquopy itself.
* `target` contains build processes for Python and its dependencies.
* `server/pypi` contains build processes for third-party Python packages.

The open-source demo apps are contained in separate repositories under
https://github.com/chaquo/.


## Build

For build instructions, see the README files in each subdirectory.

Or to build everything at once, follow the instructions below on a Linux x86-64 machine:

If necessary, install Docker using the [instructions on its
website](https://docs.docker.com/install/#supported-platforms).

Make sure all submodules are up to date:

    git submodule init && git submodule update

Then run the script `build-maven.sh`. This will generate a `maven` directory containing the
Chaquopy repository.

To use this repository to build an app, edit the `repositories` block in your `settings.gradle`
or `build.gradle` file to [declare your
repository](https://docs.gradle.org/current/userguide/declaring_repositories.html#sec:declaring_multiple_repositories)
before `mavenCentral`. Either an HTTP URL or a local path can be used.
