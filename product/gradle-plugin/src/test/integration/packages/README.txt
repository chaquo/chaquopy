The package files in dist/ and ../data/ were generated as follows:

* Some of the simpler ones were built using the script src/native/build.py.

* Others were built by running one or both of the following commands in the corresponding
  src/ subdirectory:

    python setup.py bdist_wheel --universal
    python setup.py sdist

Some of the packages were then renamed to meet the needs of the tests.

However, unless a test actually requires a package file, it's better to put the Python
source tree inside the test's own data directory, and install it like this:

     pip {
         install "./dir_name"
     }
