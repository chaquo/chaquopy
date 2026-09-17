# Building wheels for Android

The recommended way to build Android-compatible wheels for Python 3.13 or later is to
use [cibuildwheel](https://cibuildwheel.pypa.io/en/stable/platforms/#android). Despite
the name, the tool is not limited to CI environments; it can be run locally on macOS and
Linux machines.

Many projects already use cibuildwheel to manage publication of binary wheels, but even
if they don't, it's easy to use cibuildwheel for Android alone. For examples of how to
add Android support to an existing package, see
[here](https://github.com/chaquo/chaquopy/issues/1417#issuecomment-3564326948).

For Python 3.12 and older, there is also a Chaquopy-specific build tool documented in
README-old.md.


## Using a package in your app

.whl files can be built into your app using the [`pip`
block](https://chaquo.com/chaquopy/doc/current/android.html#requirements) in your
`build.gradle` file:

* Add an `options` line to pass
  [`--find-links`](https://pip.pypa.io/en/stable/cli/pip_install/#cmdoption-find-links)
  with the location of the directory that contains the wheels.
* Add an `install` line giving the name of your package.
