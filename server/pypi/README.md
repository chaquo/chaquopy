# Building wheels for Android

The recommended way to build Android-compatible wheels for Python 3.13 or later is to
use [cibuildwheel](https://cibuildwheel.pypa.io/en/stable/platforms/#android). Despite
the name, the tool is not limited to CI environments; it can be run locally on macOS and
Linux machines. Many projects already use cibuildwheel, but even if they don't, it's
easy to use it for Android alone.

For examples of how to add Android support to a package, see the [issues labeled
"upstreamed"](https://github.com/chaquo/chaquopy/issues?q=is%3Aissue+label%3Aupstreamed)
and search for the word "official".

The following sections of cibuildwheel's documentation will also be useful:

* [Android](https://cibuildwheel.pypa.io/en/stable/platforms/#android), for the
  prerequisites you need to install.
* [Getting started](https://cibuildwheel.pypa.io/en/stable/setup/): you'll want to use
  the `--platform android` option, or
  [`--only`](https://cibuildwheel.pypa.io/en/stable/options/#command-line) with one of
  the [Android build
  identifiers](https://cibuildwheel.pypa.io/en/stable/options/#build-skip).

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
