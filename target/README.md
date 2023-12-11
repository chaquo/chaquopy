# Chaquopy target

This directory contains scripts to build Python for Android.


## Supporting libraries

Before building Python, the correct versions of the supporting libraries must already be
present in the `prefix` subdirectory:

* Bzip2, libffi and xz use static libraries, so you must build them yourself, using the
  commands from build-all.sh.
* SQLite and OpenSSL use dynamic libraries, so you may either build them yourself in the
  same way, or get pre-built copies using the download-target.sh and unpackage-target.sh
  scripts, as shown in ci.yml.


## Python

Update Common.java with the version you want to build, and the build number you want to
give it.

Run build-and-package.sh, as shown in build-all.sh. This will create a release in the
`maven` directory in the root of this repository. If the packaging phase fails, e.g.
because the version already exists, then rather than doing the whole build again, you
can re-run package-target.sh directly.

If this is a new major.minor version, do the "Adding a Python version" checklist below.

Run the PythonVersion integration tests.

Use the demo app to run the Python and Java unit tests on the full set of pre-release
devices (see release/README.md).

To publish the build, follow the "Public release" instructions in release/README.md.
Once a version has been published on Maven Central, it cannot be changed, so any fixes
must be released under a different build number.


## Adding a Python version

Add it to Common.java.

Add it to build-all.sh.

In test_gradle_plugin.py, update the `PYTHON_VERSIONS` assertion.

Update the `MAGIC` lists in test_gradle_plugin.py and pyc.py.

Update documentation:
* "Python version" in android.rst
* "Python versions" in versions.rst

To allow running the unit tests, build any packages used by the demo app.

When building the other packages:

* For each package, in dependency order:
  * Update to the current stable version, unless it's been updated recently, or updating
    would take a lot of work which wouldn't be justified by user demand.
  * Review patches and build scripts to see if there are any workarounds which are no
    longer necessary.
* When finished:
  * Clear out any bad builds before copying them to the public repository.
  * Notify any users who requested new versions.


## Removing a Python version

Update all the things listed in the "Adding a Python version" section.

Search source code for `(python|version_info) *[<>=]* *[0-9]` to see if any workarounds
can now be removed.

Check if any modules can be removed from `BOOTSTRAP_NATIVE_STDLIB` in PythonTasks.kt.


## Changing the default Python version

Update `DEFAULT_PYTHON_VERSION` in Common.java.

Update the pythonX.Y scripts in integration/data/BuildPython.

See the note about the default Python micro version in
.github/actions/setup-python/action.yml.

(REST OF LIST TBD)
