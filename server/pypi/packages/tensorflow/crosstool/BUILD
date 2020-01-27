# Chaquopy: see https://docs.bazel.build/versions/0.29.1/tutorial/cc-toolchain-config.html

package(default_visibility = ["//visibility:public"])

cc_toolchain_suite(
  name = 'crosstool',
  toolchains = {
    # Use the Android ABI name as the CPU name, for compatibility with Bazel's standard
    # Android support.
    '%{CHAQUOPY_ABI}': ':cc-compiler-chaquopy',
    '%{CHAQUOPY_ABI}|compiler': ':cc-compiler-chaquopy',
   },
)

filegroup(
    name = "empty",
    srcs = [],
)

cc_toolchain(
  name = 'cc-compiler-chaquopy',
  toolchain_identifier = 'chaquopy_ndk',
  toolchain_config = ":chaquopy_ndk_config",
  all_files = ':empty',
  compiler_files = ':empty',
  dwp_files = ':empty',
  linker_files = ':empty',
  objcopy_files = ':empty',
  strip_files = ":empty",
  supports_param_files = 1,
)

load(":cc_toolchain_config.bzl", "cc_toolchain_config")
cc_toolchain_config(name = "chaquopy_ndk_config")
