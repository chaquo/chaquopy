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

* `product/gradle-plugin` contains the Chaquopy Gradle plugin.
* `product/runtime` contains the Chaquopy runtime libraries.
* `target` contains build scripts for Python and its supporting libraries.
* `server/pypi` contains build scripts for third-party Python packages.


## Build

For build instructions, see the README files in each subdirectory. All build outputs
are stored in the `maven` directory.

To use this repository to build an app, edit the `repositories` block in your
`settings.gradle` or `build.gradle` file to [declare your
repository](https://docs.gradle.org/current/userguide/declaring_repositories.html#sec:declaring_multiple_repositories)
before `mavenCentral`. Either an HTTP URL or a local path can be used.
