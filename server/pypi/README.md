# Chaquopy packages

This directory contains the build-wheel tool, which produces Android .whl files compatible
with Chaquopy.

build-wheel can build .whl files for all [Android
ABIs](https://developer.android.com/ndk/guides/abis) (armeabi-v7a, arm64-v8a, x86 and
x86_64). However, the tool itself only runs on Linux x86-64. If you don't already have a
Linux machine available, a cheap virtual server from somewhere like DigitalOcean will do
just fine.


## Setup

First, clone this repository.

Then, go to [this Maven Central
page](https://repo.maven.apache.org/maven2/com/chaquo/python/target/) and select which
Python version you want to build for. Within a given Python minor version (e.g. 3.8),
you should usually use the newest version available. Then use `download-target.sh` to
download it into `maven` in the root of this repository. For example, to download
version 3.8.16-0, run:

    target/download-target.sh maven/com/chaquo/python/target/3.8.16-0

You'll also need a matching version of Python installed on your build machine. For
example, if you're building for Python 3.8, then `python3.8` must be on the PATH. You may
be able to get this from your distribution, or from an unofficial package repository.
Otherwise, here's how to install it with Miniconda:

* Download the installer from <https://docs.conda.io/en/latest/miniconda.html>.
  * To work around <https://github.com/conda/conda/issues/10431>, run it like this:
    `bash Miniconda3-latest-Linux-x86_64.sh`.
  * When asked whether to run `conda init`, answer yes, and follow the instructions.
* `conda create -n build-wheel python=X.Y`, where `X.Y` is the Python version you want to
  build for.
* `conda activate build-wheel`

Export the `ANDROID_HOME` environment variable to point at your Android SDK. If you don't
already have the SDK, here's how to install it:

* Download the "Command line tools" from <https://developer.android.com/studio>.
* Create a directory `android-sdk/cmdline-tools`, and unzip the command line tools package
  into it.
* Rename `android-sdk/cmdline-tools/cmdline-tools` to `android-sdk/cmdline-tools/latest`.
* `export ANDROID_HOME=/path/to/android-sdk`

Use pip to install the `requirements.txt` in this directory.

Use your distribution's package manager to install the following build tools:
* patch
* patchelf

Depending on which package you're building, you may also need additional tools. Most of
these can be installed using your distribution. Some of them have special entries in the
`build` requirements section of meta.yaml:

* `fortran`: You must install the Fortran compiler from
  [here](https://github.com/mzakharo/android-gfortran/releases/tag/r21e). Create a
  `fortran` subdirectory in the same directory as this README, and unpack the .bz2 files
  into it.
* `rust`: `rustup` must be on the PATH.


## Building a package

Run build-wheel from this directory as follows:

    ./build-wheel.py --python X.Y --abi ABI PACKAGE

Where:

* `X.Y` is the Python version you set up above, e.g. `3.8`.
* `ABI` is an [Android
  ABI](https://chaquo.com/chaquopy/doc/current/android.html#android-abis).
* `PACKAGE` is a subdirectory of `packages` in this directory, or the path to another
  directory laid out in the same way (see "adding a package" below).

The resulting .whl files will be generated in the `dist` subdirectory of this directory.


## Adding a package

Under `packages` in this directory, create a recipe directory named after the package,
normalized according to [PEP
503](https://peps.python.org/pep-0503/#normalized-names). Alternatively, you can create
this directory somewhere else, and pass its path when calling build-wheel.

Inside the recipe directory, add the following files:

* A `meta.yaml` file. This supports a subset of Conda syntax, defined in `meta-schema.yaml`.
* For non-Python packages, a `build.sh` script.
* If necessary, a `patches` subdirectory containing patch files.

Here are some examples of existing recipes:

* multidict: a minimal example, downloaded from PyPI.
* cython-example: a minimal example, built from a local directory.
* python-example: a pybind11-based package, downloaded from a Git repository.
* cmake-example: similar to python-example, but uses CMake.
* chaquopy-libzmq: a non-Python library, downloaded from a URL.
* pyzmq: a Python package which depends on chaquopy-libzmq. A patch is used to help
  `setup.py` find the library.
* scikit-learn: lists several requirements in `meta.yaml`:
  * The "build" requirement (Cython) will be installed automatically.
  * The "host" requirements (NumPy etc.) must be downloaded manually from [the public
    repository](https://chaquo.com/pypi-13.1/). Save them into a corresponding
    subdirectory of `dist` (e.g. `dist/numpy`), before running the build.

Then run build-wheel as shown above.

If any changes are needed to make the build work, the easiest procedure is:

* In the recipe directory, enter the `build` subdirectory and locate the package's source
  code.
* Edit the source code as necessary.
* Re-run build-wheel with the `--no-unpack` option to prevent your changes from being
  overwritten.
* Once everything's working, save your changes in a patch file in the recipe's `patches`
  subdirectory. This will be applied automatically in any future builds.


## Using a package in your app

.whl files can be built into your app using the [`pip`
block](https://chaquo.com/chaquopy/doc/current/android.html#requirements) in your
`build.gradle` file. First, add an `options` line to pass
[`--extra-index-url`](https://pip.pypa.io/en/stable/cli/pip_install/#cmdoption-extra-index-url)
with the location of the `dist` directory mentioned above. Either an HTTP URL or a local path
can be used. Then add an `install` line giving the name of your package.


## Testing a package

The pkgtest app in this directory is a test harness for checking package builds. Here's
how to use it.

First, create a `test.py` file in the recipe directory, or a `test` subdirectory with an
`__init__.py` if you need to include additional files. This should contain a `TestCase`
class which does some basic checks on the package. See the existing recipes for
examples: usually we base them on the package's own tutorial.

Open the pkgtest app in Android Studio, and temporarily edit `app/build.gradle` as
follows:

* Set `PACKAGES` to the package's name.
* Set `python { version }` to the Python version you want to test.
* Set the `--extra-index-url` as described above.
* Set `abiFilters` to the ABIs you want to test.

Then run the app.
