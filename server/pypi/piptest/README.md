Build scripts can run arbitrary code, so when running these tests on unchecked package lists,
you should use an environment without access to anything sensitive. To make this easier, the
tests are stored in a separate repository from the product source code.

Before running:

* Install Android SDK, and create `src/local.properties` with the `sdk.dir` property giving its
  location.
* Copy Chaquopy Gradle plugin JAR into `src`.
