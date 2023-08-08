package com.chaquo.python.internal;

import org.gradle.api.*;

/** Constants and utilities shared between multiple build scripts */
public class BuildCommon {

    // The following properties file should be created manually, as described in
    // product/README.md. It's also used in test_gradle_plugin.py.
    public static String localProperty(Project project, String key, String defaultValue = null) {
        def localProps = new Properties()
        localProps.load(project.rootProject.file('local.properties').newDataInputStream())
        def result = localProps.getProperty(key, defaultValue)
        if (result == null) {
            throw new GradleException("'$key' is missing from local.properties")
        }
        return result
    }

    public static String androidHome(Project project) {
        def home = System.getenv("ANDROID_HOME")
        if (home != null) {
            return home
        }

        try {
            return localProperty(project, "sdk.dir")
        } catch (GradleException e) {
            throw new GradleException(
                "SDK location not found. Define location with sdk.dir in the " +
                "local.properties file or with an ANDROID_HOME environment variable.")
        }
    }

}
