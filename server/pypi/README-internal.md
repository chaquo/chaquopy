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
* A clean install

Repeat the build and test on all other Python versions.

Move the wheels to the public package repository.

Notify any users who requested this package on GitHub or elsewhere.


## Testing the most popular packages

### Get the list

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
Use a 7-day window to avoid any bias from weekday/weekend differences, and make it end
at least 2 days in the past in case there's any delay.

### Run the tests

Build scripts can run arbitrary code, so these tests must be done within Docker, like
this:

`cat pypi-downloads-20210828-20210903.csv | head -n 1000 | cut -d, -f1 | xargs -n 1 -P $(nproc) docker run --rm -v $(pwd)/log:/root/server/pypi/piptest/log -v $ANDROID_HOME:/root/android-sdk chaquopy-piptest`

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
  * `pattern='Failed to install|No matching distribution found for|Failed building wheel for'; cat log/* | grep -Eia "$pattern" | sed -E "s/.*($pattern)//; s/[ (]from.*//" | sort | uniq -c | sort -nr`

Do whatever's necessary to maintain the 90% support level mentioned in
product/runtime/docs/sphinx/android.rst.
