# Based loosely on https://github.com/bazelbuild/bazel/wiki/Building-with-a-custom-toolchain

package(default_visibility = ["//visibility:public"])

# This is the entry point for --crosstool_top.
#
# The cc_toolchain rule used is found by:
#
# 1. Finding the appropriate toolchain in the CROSSTOOL file based on the --cpu
#    and --compiler command line flags (if they exist, otherwise using the
#    "default_target_cpu" / "default_toolchain" fields in the CROSSTOOL file)
# 2. Concatenating the "target_cpu" and "compiler" fields of the toolchain in
#    use and using that as a key in the map below.
cc_toolchain_suite(
  name = 'crosstool',
  toolchains = {
    'chaquopy|compiler': ':cc-compiler-chaquopy',
  },
)

filegroup(
    name = "empty",
    srcs = [],
)

cc_toolchain(
  name = 'cc-compiler-chaquopy',
  all_files = ':empty',
  compiler_files = ':empty',
  cpu = 'chaquopy',
  dwp_files = ':empty',
  dynamic_runtime_libs = [':empty'],
  linker_files = ':empty',
  objcopy_files = ':empty',
  static_runtime_libs = [':empty'],
  strip_files = ":empty",
  supports_param_files = 1,
)
