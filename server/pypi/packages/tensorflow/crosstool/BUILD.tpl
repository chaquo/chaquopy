# Chaquopy: see https://docs.bazel.build/versions/0.21.0/tutorial/crosstool.html

package(default_visibility = ["//visibility:public"])

cc_toolchain_suite(
  name = 'crosstool',
  toolchains = {
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
  all_files = ':empty',
  compiler_files = ':empty',
  cpu = '%{CHAQUOPY_ABI}',
  dwp_files = ':empty',
  dynamic_runtime_libs = [':empty'],
  linker_files = ':empty',
  objcopy_files = ':empty',
  static_runtime_libs = [':empty'],
  strip_files = ":empty",
  supports_param_files = 1,
)
