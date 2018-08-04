# Development environment setup

(NOTE: This procedure has not been fully tested and may be incomplete.)

Install the following prerequisites:

* Java 8 or later, either on the `PATH` as `java`, or pointed to by `JAVA_HOME`.
* Python 2 and 3, on the `PATH` as `python2`/`python3` (on Linux) or `py` (on Windows).
* Android SDK, including the following packages:
   * Build Tools
   * CMake
   * NDK
   * SDK Platform version corresponding to `COMPILE_SDK_VERSION` in
     product/buildSrc/src/main/java/com/chaquo/python/Common.java.
* Crystax NDK 10.3.2

$CRYSTAX_DIR/sources/python must contain libraries and includes for the currently-supported
Python minor versions (differences in the micro version don't matter). If building against a
Python version which comes with Crystax, the Crystax copies can be used. Otherwise, generate
them using the process documented in target/README.md, or copy them from another machine where
this has already been done.

Create product/local.properties with the properties listed in product/runtime/build.gradle.
