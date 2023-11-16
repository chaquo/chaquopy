// Top-level build file where you can add configuration options common to all
// sub-projects/modules.
buildscript {
    // The version file can't be read within the plugins block, because there's no way
    // to determine the project directory there.
    System.setProperty("chaquopyVersion", file("../VERSION.txt").readText().trim())
}

plugins {
    id("com.android.application") version "8.1.3" apply false
    id("org.jetbrains.kotlin.android") version "1.8.10" apply false
    id("com.chaquo.python") version System.getProperty("chaquopyVersion") apply false
}
