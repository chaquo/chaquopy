# Adding a new package

Create a new subdirectory in packages/. Its capitalization must exactly match the package's
canonical capitalization on PyPI.

In the package subdirectory, create a test.py file to run on a target installation. This should
contain a unittest.TestCase subclass which imports the package and does some basic sanity checks.

Run build-wheel.py once for each desired combination of version and ABI.
