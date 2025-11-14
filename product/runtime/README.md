# Chaquopy runtime libraries


## Build

For build instructions, see the README in the parent directory.


## Test

The runtime unit tests are mainly run on Android via the demo app in the root of this
repository. However, the non-Android-specific features, such as the Java/Python
interface, can also be tested directly on the build platform.

Prerequisities (on Windows, these must be the MSYS2 versions):

* GCC and binutils.

* The same Python major.minor version as Chaquopy uses by default.

  * On Linux, install it from your distribution, or use Miniconda. Make sure you also
    include the development headers (e.g. `pythonX.Y-dev` on Debian).

  * On Mac, download it from https://python.org/.

  * On Windows, install it using MSYS2's `pacman`. If MSYS2 has already moved on to a
    later Python version, download the correct version from
    http://repo.msys2.org/mingw/mingw64/ and install it with `pacman -U`.

    Make sure your PATH is set so that invocations of `pythonX.Y` will use the MSYS2
    version.

The tests are run by the Gradle tasks `runtime:testPython` and `runtime:testJava`. Or
run `runtime:check` to test everything at once.
