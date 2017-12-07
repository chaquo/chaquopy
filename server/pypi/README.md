# Adding a new package

Create a new subdirectory in packages/. Its capitalization must exactly match the package's
canonical capitalization on PyPI.

In the package subdirectory:

* Create a test.py file to run on a target installation. This should contain a
  unittest.TestCase subclass which imports the package and does some basic sanity checks.
* If necessary, add a `patches` subdirectory containing patch files.
* Create a version.txt file to specify which version number should be tested by the pkgtest app.

Run build-wheel.py once for each desired combination of package version, Python version and ABI.

Copy the resulting wheels from packages/*/dist to the package repository.

Test on all platforms using the pkgtest app.
