package com.chaquo.python.internal;

import java.io.*;
import java.util.*;


/** Constants and utilities shared between the Gradle plugin, the runtime, and their
 * respective build scripts. */
public class Common {
    // Minimum Android Gradle plugin version
    public static final String MIN_AGP_VERSION = "7.0.0";

    // This should match api_level in target/android-env.sh.
    public static final int MIN_SDK_VERSION = 24;

    public static final int COMPILE_SDK_VERSION = 34;

    public static final Map<String, String> PYTHON_VERSIONS = new LinkedHashMap<>();
    static {
        // Version, build number
        PYTHON_VERSIONS.put("3.8.20", "0");
        PYTHON_VERSIONS.put("3.9.20", "0");
        PYTHON_VERSIONS.put("3.10.15", "0");
        PYTHON_VERSIONS.put("3.11.10", "0");
        PYTHON_VERSIONS.put("3.12.7", "0");
        PYTHON_VERSIONS.put("3.13.0", "0");
    }

    public static List<String> PYTHON_VERSIONS_SHORT = new ArrayList<>();
    static {
        for (String fullVersion : PYTHON_VERSIONS.keySet()) {
            PYTHON_VERSIONS_SHORT.add(
                fullVersion.substring(0, fullVersion.lastIndexOf('.')));
        }
    }

    // This is the version with the best set of native packages in the repository.
    public static final String DEFAULT_PYTHON_VERSION = "3.8";

    // Wheel tags (PEP 425).
    public static final String PYTHON_IMPLEMENTATION = "cp";  // CPython

    public static List<String> supportedAbis(String pythonVersion) {
        if (!PYTHON_VERSIONS_SHORT.contains(pythonVersion)) {
            throw new IllegalArgumentException(
                "Unknown Python version: '" + pythonVersion + "'");
        }

        List<String> result = new ArrayList<>();
        result.add("arm64-v8a");
        result.add("x86_64");
        if (Arrays.asList("3.8", "3.9", "3.10", "3.11").contains(pythonVersion)) {
            result.add("armeabi-v7a");
            result.add("x86");
        }
        result.sort(null);  // For testing error messages
        return result;
    }

    // Subdirectory name to use within assets, getFilesDir() and getCacheDir()
    public static final String ASSET_DIR = "chaquopy";

    public static String assetZip(String type) {
        return assetZip(type, null);
    }

    public static String assetZip(String type, String abi) {
        // We need to prevent our ZIP files from being compressed within the APK. This
        // wouldn't save much space (because the files within the ZIP are already
        // compressed), but it would seriously harm performance of AssetFinder, because
        // it would have to read and decompress all the intermediate data every time it
        // seeks within the ZIP.
        //
        // Unfortunately .zip is not one of the default noCompress extensions
        // (frameworks/base/tools/aapt2/cmd/Link.cpp). We used to monkey-patch the noCompress
        // method, but that doesn't carry over from an AAR to the final APK. So we'll just have
        // to rename the AssetFinder ZIPs to one of the extensions in the default list. We use
        // something obscure so that Chaquopy developers can configure their file explorer to
        // treat it as a ZIP without causing any inconvenience.
        String ext = ".imy";
        if (abi == null) {
            return type + ext;
        } else {
            return type + "-" + abi + ext;
        }
    }

    // Parameters for assetZip
    public static final String ABI_COMMON = "common";
    public static final String ASSET_BOOTSTRAP = "bootstrap";
    public static final String ASSET_APP = "app";
    public static final String ASSET_REQUIREMENTS = "requirements";
    public static final String ASSET_STDLIB = "stdlib";

    // Other assets
    public static final String ASSET_BOOTSTRAP_NATIVE = "bootstrap-native";
    public static final String ASSET_BUILD_JSON = "build.json";
    public static final String ASSET_CACERT = "cacert.pem";

    public static String osName() {
        String property = System.getProperty("os.name");
        String[] knownNames = new String[] {"linux", "mac", "windows"};
        for (String name : knownNames) {
            if (property.toLowerCase(Locale.ENGLISH).startsWith(name)) {
                return name;
            }
        }
        throw new RuntimeException("unknown os.name: " + property);
    }

    public static String findExecutable(String name) throws FileNotFoundException {
        File file = new File(name);
        if (file.isAbsolute()) {
            if (! file.exists()) {
                throw new FileNotFoundException("'" + name + "' does not exist");
            }
            return name;
        }

        // The default PATH on Mac is /usr/bin:/bin:/usr/sbin:/sbin. However, apps can't
        // install anything into these locations, so the python.org installers use
        // /usr/local/bin instead. This directory may also appear to be on the default
        // PATH, but this is because it's listed in /etc/paths, which only affects
        // shells, but not other apps like Android Studio and its Gradle subprocesses.
        //
        // As of Gradle 6.9, this appears to be unnecessary (#821). So once the
        // `product` project is using a newer version than that, we can remove this
        // method and let Gradle find executables itself.
        List<String> path = new ArrayList<>();
        String osName = System.getProperty("os.name").toLowerCase();
        if (osName.startsWith("mac")) {
            final String ETC_PATHS = "/etc/paths";
            try (BufferedReader reader = new BufferedReader(new FileReader(ETC_PATHS))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    path.add(line);
                }
            } catch (IOException e) {
                System.out.println("Warning: while reading " + ETC_PATHS + ": " + e);
            }
        }
        Collections.addAll(path, System.getenv("PATH").split(File.pathSeparator));

        List<String> exts = new ArrayList<>();
        exts.add("");
        if (osName.startsWith("win")) {
            exts.add(".exe");
            exts.add(".bat");
        }

        for (String dir : path) {
            for (String ext : exts) {
                file = new File(dir, name + ext);
                if (file.exists()) {
                    return file.toString();
                }
            }
        }
        throw new FileNotFoundException("Couldn't find '" + name + "' on PATH");
    }

}
