# Introduction

This directory contains the build-wheel tool, which produces Android .whl files for Chaquopy,
and iOS/tvOS/watchOS .whl files for Beeware.

## Android

Android builds are only supported on Linux x86-64. However, the resulting .whls can be built
into an app on any supported Android build platform, as described in the [Chaquopy
documentation](https://chaquo.com/chaquopy/doc/current/android.html#requirements).

## iOS/tvOS/watchOS

iOS build are supported on both x86-64 and M1; however, not all packages currently build.
See the notes at the end fo this document.

# Usage

Install the requirements in `requirements.txt`, then run `build-wheel.py --help` for more
information.

# Adding a new package

Create a recipe directory in `packages`. Its name must be in PyPI normalized form (PEP 503).
Alternatively, you can create this directory somewhere else, and pass its path when calling
`build-wheel.py`.

Inside the recipe directory, add the following files.

* A `meta.yaml` file. This supports a subset of Conda syntax, defined in `meta-schema.yaml`.
* A `test.py` file (or `test` package), to run on a target installation. This should contain a
  unittest.TestCase subclass which imports the package and does some basic checks.
* For non-Python packages, a `build.sh` script. See `build-wheel.py` for environment variables
  which are passed to it.

## Android

Run `build-wheel.py` for x86_64. If any changes are needed to make the build work, edit the
package source code in the `build` subdirectory, and re-run `build-wheel.py` with the
`--no-unpack` option. Then copy the resulting wheel from `dist` to a private package repository
(edit `--extra-index-url` in `pkgtest/app/build.gradle` if necessary).

Temporarily add the new package to `pkgtest/app/build.gradle`, and set `abiFilters` to
x86_64 only.

Unless the package depends on changes in the development version, edit `pkgtest/build.gradle`
to use the current stable Chaquopy version. Then run the tests.

If this is a new version of an existing package, we should check that it won't break any
existing apps with unpinned version numbers. So temporarily edit `pkgtest/build.gradle` to
use the oldest Chaquopy version which supported this package with this Python version. If
necessary, also downgrade the Android Gradle plugin, and Gradle itself. Then run the tests.

If any changes are needed to make the tests work, increment the build number in `meta.yaml`
before re-running `build-wheel.py` as above.

Once the package itself is working, also test any packages that list it as a requirement in
meta.yaml, since these usually indicate a dependency on native interfaces which may be less
stable. Include these packages in all the remaining tests.

Once everything's working on x86_64, save any edits in the package's `patches` directory,
then run `build-wheel.py` for all other ABIs, and copy their wheels to the private package
repository.

Restore `abiFilters` to include all ABIs. Then test the app with the same Chaquopy versions
used above, on the following devices, with at least one device being a clean install:

* x86 emulator with minSdkVersion, or API 18 if "too many libraries" error occurs (#5316)
* x86_64 emulator with targetSdkVersion
* x86_64 emulator with API 21 (or 23 before Chaquopy 7.0.3)
* Any armeabi-v7a device
* Any arm64-v8a device

Move the wheels to the public package repository.

Update any GitHub issues, and notify any affected users who contacted us outside of GitHub.

## iOS/tvOS/watchOS

### Quickstart

Obtain a Beeware [Apple Support
package](https://github.com/beeware/Python-Apple-support) for the Python version
you are using, and unpack the support package into a folder that matches the Python
version you are supporting (i.e., unpack a 3.10 support package into a folder named
`3.10`)

Then run:

    ./make-deps.sh <path to support folder> <python version>
    ./make.sh <path to support folder> <python version>

For example, if you put the support folder in the same directory as this README, and
you want to build Python 3.10, run:

    ./make-deps.sh ./support 3.10
    ./make.sh ./support 3.10

Once you've run `make-deps.sh` for a single Python version, you don't need to run it
for other Python versions; it is sufficient to just run `./make.sh`.

When each script finishes, it will tell you how many packages were built, and how
many were expected. If there is a discrepancy, you can investigate further.

### Individual packages

Obtain a Beeware [Apple Support
package](https://github.com/beeware/Python-Apple-support) for the Python version
you are using, and unpack the support package into a folder that matches the Python
version you are supporting (i.e., unpack a 3.10 support package into a folder named
`3.10`). The location that contains the `3.10` folder will be provided to the
`--toolchain` argument.

If you want to build a package that uses `cmake`, you will also need to obtain
a macOS install of cmake. Get a 'tar.gz' package, and unpack it; copy the `CMake.app`
into the same folder that contains the support package folder. If you've done this
correctly, you should have a folder that looks something like:

  - `toolchain`
    - `3.10`
      - `VERSIONS`
      - `Python.xcframework`
      - `platform-site`
      - `python-stdlib`
    - `CMake.app`

The name and location of the `toolchain` folder doesn't matter; this is the folder
that will be provided as the `--toolchain` argument to `build-wheel.py`.

When you run `build-wheel.py` on a recipe, it will:

* Build an iOS/tvOS arm64 wheel, or a watchOS arm64_32 wheel
* Build an iOS/tvOS/watchOS Simulator arm64 wheel
* Build an iOS/tvOS/watchOS Simulator x86_64 wheel
* Use `lipo` to merge each `.so` file in the Simulator wheels into a "fat" binary
* Merge the iOS and iOS simulator wheels into a single "fat" wheel.

The fat wheel will contain 2 `.so` files for every binary module - one for
devices, and one for the simulator.

As on macOS, an iOS/tvOS/watchOS binary module is statically linked against all
dependencies. For example, the Pillow binary modules statically link the
contents of libjpeg, libpng and libfreetype into the .so files contained in the
`.whl` file. The wheel will not contain `.so` files for any dependencies, nor
will you need to install any extra dependencies.

If a wheel has a dependency on a binary library that the Apple Support project
builds (BZip2, XZ, OpenSSL or libFFI), you should clone the Apple Support repository
and run `make wheels` in that repository. Once that build completes, copy the
contents of the `wheels/dist` directory into the `server/pypi/dist` folder in
this reposistory. You can then reference those wheels as a host dependency for
your new library/

If a wheel has a dependency on any other binary library (like `libpng`), there
will be a `chaquopy-` prefixed recipe for the library. This recipe will produce
a wheel - however, this is a "build-time" wheel; it will only contain the `.a`
library, which can be used to link into the projects that use it. There is no
need to distribute the `chaquopy-*` wheels.

### Configure-based projects

If the project includes a `configure` script, you will likely need to provide
a patch for `config.sub`. `config.sub` is the tools used by `configure` to identify
the architecture and machine type; however, it doesn't currently recognize the
host triples used by Apple. If you get the error:

    checking host system type... Invalid configuration `arm64-apple-ios': machine `arm64-apple' not recognized
    configure: error: /bin/sh config/config.sub arm64-apple-ios failed

you will need to patch `config.sub`. There are several examples of patched
`config.sub` scripts in the packages contained in this repository, and in the
Python-Apple-support project; it is quite possible one of those patches can be
used for the library you are trying to compile. The `config.sub` script has
a datestamp at the top of the file; that can be used to identify which patch
you will need.

### Other known problems:

At this time, there are also problems building recipes that:

* Use Cmake in the build process
* Use Rust in the build process
* Have a dependency on libfortran or a Fortran compiler
* Have a vendored version of distutils
