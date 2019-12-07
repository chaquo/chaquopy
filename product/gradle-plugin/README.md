# Browsing Android Gradle plugin source code

Create a Gradle Java project in IntelliJ (NOT an Android app project) and add the Android
Gradle plugin to its compile classpath. Once the IDE has synced, you'll be able to find classes
with double-shift and use all the standard IDE navigation functions.

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
