# Browsing Android Gradle plugin source code

Create a fresh Gradle project in IntelliJ and add the Android Gradle plugin to its compile
classpath. At least in 3.2.0-beta05, it appears that the JAR contains source code, so you can
find classes with double-shift and use all the standard IDE navigation functions.

Alternatively, to get the original source repositories, either use the Google "repo" tool, or
do the following:

* Check out the following Android repositories at the desired version:
   * manifest
   * tools/buildSrc
   * tools/base
   * tools/gradle
   * Any other repositories referenced from tools/base/.idea/modules.xml.
* Copy files from tools/buildSrc as indicated in the manifest.
* Open tools/base as a project in IDEA.
