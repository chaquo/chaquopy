# Chaquopy packages - internal notes

This file contains checklists for use by Chaquopy's own developers.


## Releasing a package

Build the package, as described in README.md. Start with Chaquopy's default Python
version, and whichever ABI is most convenient for you to test.

Test the resulting .whl file using the pkgtest app, as described in README.md. Use the
current stable Chaquopy version, unless the package depends on changes in the development
version.

If any changes are needed to make the tests work, increment the build number in
`meta.yaml` before re-running build-wheel.

Once the package itself is working, also test any packages that list it as a requirement
in their `meta.yaml` files, since these usually indicate a dependency on native interfaces
which may be less stable. Include these packages in all the remaining tests.

Once everything's working on this ABI, save any edits in the package's `patches`
directory. Then run build-wheel for all other ABIs.

Restore `abiFilters` to include all ABIs, and test them all, with at least one device
being each of the following:

* A physical device (on all ABIs if possible)
* minSdk (on all ABIs if possible)
* targetSdk
* 16 KB pages
* A clean install

Repeat the build and test on all other Python versions.

Move the wheels to the public package repository.

Notify any users who requested this package on GitHub or elsewhere.


## Testing the most popular packages

### Run the tests

Get the [PyPI statistics in CSV format](https://hugovk.github.io/top-pypi-packages/).

Build scripts can run arbitrary code, so these tests must be done within Docker, like
this:

* `cd piptest`
* `docker build -t chaquopy-piptest .`
* `cat path/to/top-pypi-packages.csv | tail -n +2 | head -n 1000 | cut -d, -f2 | tr -d '"' | xargs -n 1 -P $(nproc) docker run --rm -v $(pwd)/log:/root/server/pypi/piptest/log -v $(pwd)/../../../maven:/root/maven chaquopy-piptest`
* This will test against the Chaquopy build from your local `maven` directory. To test
  against the newest version on Maven Central, remove the `-v ... maven` option.

### Analyze the results

The results are written to `piptest/log`, and can be summarized as follows:
* Successful: search for `BUILD SUCCESSFUL`.
* Failed: search for `BUILD FAILED`.

Check the following:

* Logs which don't contain either a success or a failure message.
* Packages with an error other than "no matching distribution" (case-insensitive).
* Packages which took more than 3 minutes. Even if they succeeded, this may indicate
  that they were doing something wrong:
  * `grep -Erl 'BUILD (SUCCESSFUL|FAILED) in [3-9]m' log`
