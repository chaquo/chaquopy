# Chaquopy

This repository contains the following components:

* `product` contains Chaquopy itself.
* `target` contains build processes for Python and its dependencies.
* `server/pypi` contains build processes for third-party Python packages.

The open-source demo apps are contained in separate repositories available at [https://github.com/chaquo/].


# Build

A Linux x86-64 machine with Docker is required. If necessary, install Docker using the
[instructions on its website](https://docs.docker.com/install/#supported-platforms).

Make sure all submodules are up to date:

    git submodule init && git submodule update

Then run the script `build-maven.sh`. This will generate a `maven` directory containing the
Chaquopy repository.

To use this repository to build an app, edit the `repositories` block in your `settings.gradle`
or `build.gradle` file to [declare your
repository](https://docs.gradle.org/current/userguide/declaring_repositories.html#sec:declaring_multiple_repositories)
before `mavenCentral`. Either an HTTP URL or a local path can be used.
