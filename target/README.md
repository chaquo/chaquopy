# Chaquopy target

This directory contains scripts to build Python for Android. They can be run on Linux or
macOS.


## Building and testing

Update Common.java with the version you want to build, and the build number you want to
give it. Once a version has been published on Maven Central, it cannot be changed, so
any fixes must be released under a different build number.

Make sure the build machine has `pythonX.Y` on the PATH, where `X.Y` is the Python
major.minor version you want to build (e.g. `3.13`).

Run `python/build-and-package.sh X.Y`. This will create a release in the `maven`
directory in the root of this repository. If the packaging phase fails, e.g. because the
version already exists, then rather than doing the whole build again, you can re-run
package-target.sh directly.

Run the tests listed under "Adding a Python version" in product/gradle-plugin/README.md.
