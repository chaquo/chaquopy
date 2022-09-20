# Chaquopy packages

## Introduction

This directory contains the build-wheel tool, which produces Android .whl files for Chaquopy.
build-wheel itself is only supported on Linux x86-64. However, the resulting .whls can be built
into an app on any supported Android build platform, as described in the [Chaquopy
documentation](https://chaquo.com/chaquopy/doc/current/android.html#requirements).

Install the requirements in `requirements.txt`, then run `build-wheel.py --help` for more
information.


## Adding a new package

Create a recipe directory in `packages`. Its name must be in PyPI normalized form (PEP 503).
Alternatively, you can create this directory somewhere else, and pass its path when calling
`build-wheel.py`.

Inside the recipe directory, add the following files.

* A `meta.yaml` file. This supports a subset of Conda syntax, defined in `meta-schema.yaml`.
* A `test.py` file (or `test` package), to run on a target installation. This should contain a
  unittest.TestCase subclass which imports the package and does some basic checks.
* For non-Python packages, a `build.sh` script. See `build-wheel.py` for environment variables
  which are passed to it.

Run `build-wheel.py` for x86_64. If any changes are needed to make the build work, edit the
package source code in the `build` subdirectory, and re-run `build-wheel.py` with the
`--no-unpack` option. Then copy the resulting wheel from `dist` to a private package repository
(edit `--extra-index-url` in `pkgtest/app/build.gradle` if necessary).

Temporarily add the new package to `pkgtest/app/build.gradle`, and set `abiFilters` to
x86_64 only.

Unless the package depends on changes in the development version, edit `pkgtest/build.gradle`
to use the current stable Chaquopy version. Then run the tests.

If this is a new version of an existing package, we should check that it won't break any
existing apps with unpinned version numbers. So temporarily edit `pkgtest/build.gradle` to
use the oldest Chaquopy version which supported this package with this Python version. If
necessary, also downgrade the Android Gradle plugin, and Gradle itself. Then run the tests.

If any changes are needed to make the tests work, increment the build number in `meta.yaml`
before re-running `build-wheel.py` as above.

Once the package itself is working, also test any packages that list it as a requirement in
meta.yaml, since these usually indicate a dependency on native interfaces which may be less
stable. Include these packages in all the remaining tests.

Once everything's working on x86_64, save any edits in the package's `patches` directory,
then run `build-wheel.py` for all other ABIs, and copy their wheels to the private package
repository.

Restore `abiFilters` to include all ABIs. Then test the app with the same Chaquopy versions
used above, on the following devices, with at least one device being a clean install:

* x86 emulator with minSdkVersion
* x86_64 emulator with minSdkVersion (or 23 before Chaquopy 7.0.3)
* x86_64 emulator with targetSdkVersion
* Any armeabi-v7a device
* Any arm64-v8a device

Move the wheels to the public package repository.

Update any GitHub issues, and notify any affected users who contacted us outside of GitHub.


## Testing the most popular packages

### Get the lists

To list the most downloaded packages on PyPI, run the following query on
[BigQuery](https://bigquery.cloud.google.com/dataset/the-psf:pypi?pli=1). I had to create
my own Google Cloud project and run the query within that, otherwise I got the error "User
does not have bigquery.jobs.create permission in project the-psf".
```
SELECT file.project, COUNT(*) as downloads,
FROM `bigquery-public-data.pypi.file_downloads`
WHERE DATE(timestamp) BETWEEN DATE("2021-08-28") and DATE("2021-09-03")
GROUP BY file.project
ORDER BY downloads DESC
LIMIT 10000
```

Use a 7-day window to avoid any bias from weekday/weekend differences.

Or to list the number of distinct /16 netblocks attempting to install each package, run
the following script on the web server logs:

`zcat chaquo-access.log.{2..START_NUM}.gz | grep -E 'GET /pypi-(2\.1|7\.0)/.*/ HTTP.*pip/' | cut -d' ' -f2,8 | grep -Ev '^(SERVER_ADDR)' | sed -E 's|/pypi-[0-9]+\.[0-9]+/(.*)/|\1|' | sed -E 's/^([0-9]+\.[0-9]+)\.[0-9]+\.[0-9]+/\1/' | sort -k2 | uniq | uniq -f1 -c | tr -s ' ' | cut -d' ' -f2,4 | sort -k 1nr,2`

Where:

* `START_NUM` is the number of the earliest log file to include.
* `SERVER_ADDR` is a pattern matching the IP addresses from which mass piptest runs have
  been done within the given period, to exclude packages which haven't been installed by a
  real user.

### Run the tests

Build scripts can run arbitrary code, so these tests must be done within Docker, like
this:

`cat pypi-downloads-20180201-20180207.csv | head -n 1000 | cut -d, -f1 | xargs -n 1 -P $(nproc) docker run --rm -v $(pwd)/log:/root/server/pypi/piptest/log chaquopy-piptest`

### Analyze the results

The results can be summarized as follows:
* Successful: search for `BUILD SUCCESSFUL`.
* Failed: search for `BUILD FAILED`. This can be divided into:
  * Failed (native): search for `Chaquopy.cannot.compile.native.code`.
  * Failed (other). Review these to see if they indicate any bug in the build process.

You may also wish to check the following:

* Packages which took more than 2 minutes. Even if they succeeded, this may indicate that
  they were building native code with a host compiler, or doing something else they
  shouldn't be:
  * `for package in <list>; do egrep -H 'BUILD (SUCCESSFUL|FAILED) in [2-9]m' log/$package.txt; done`
* Failed requirements which many packages depend on. This will also reveal dependencies on
  packages which we do have in the repository, but with an incompatible version:
  * `pattern='Failed to install|No matching distribution found for'; cat log-pypi/* | grep -Eia "$pattern" | sed -E "s/.*($pattern)//; s/[ (]from.*//" | sort | uniq -c | sort -nr`
