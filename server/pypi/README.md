# Introduction

This directory contains the build-wheel tool, which produces Android .whl files for Chaquopy.
build-wheel itself is only supported on Linux x86-64. However, the resulting .whls can be built
into an app on any supported Android build platform, as described in the [Chaquopy
documentation](https://chaquo.com/chaquopy/doc/current/android.html#requirements).

Install the requirements in `requirements.txt`, then run `build-wheel.py --help` for more
information.


# Adding a new package

Create a new subdirectory in `packages`. Its name must be in PyPI normalized form (PEP 503).
Alternatively, you can create this subdirectory somewhere else, and use the `--extra-packages`
option when calling `build-wheel.py`.

Inside the subdirectory, add the following files.

* A `meta.yaml` file. This supports a subset of Conda syntax, defined in `meta-schema.yaml`.
* A `test.py` file (or `test` package), to run on a target installation. This should contain a
  unittest.TestCase subclass which imports the package and does some basic checks.
* For non-Python packages, a `build.sh` script. See `build-wheel.py` for environment variables
  which are passed to it.
* If necessary, a `patches` subdirectory containing patch files.

Run `build-wheel.py` once for each desired combination of package version, Python version and
ABI.

Copy the resulting wheels from `packages/<subdir>/dist` to a private package repository (edit
`--extra-index-url` in `pkgtest/app/build.gradle` if necessary).

Temporarily add the new package to `pkgtest/app/build.gradle`. If planning to
release the package before the next version of the SDK, also temporarily edit
`pkgtest/build.gradle` to test with the current released version.

Then test the app on the following devices, with at least one device being a clean install:

* x86 emulator with minSdkVersion, or API 18 if "too many libraries" error occurs (#5316)
* x86 emulator with targetSdkVersion
* x86\_64 emulator with API 23 (#5563)
* Any armeabi-v7a device
* Any arm64-v8a device

Once everything's working, move the wheels to the public package repository, and go through the
public release procedure.
