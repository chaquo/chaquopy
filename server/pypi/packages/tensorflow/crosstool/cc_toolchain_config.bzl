load("@bazel_tools//tools/cpp:cc_toolchain_config_lib.bzl", "tool_path")

def _impl(ctx):
    return cc_common.create_cc_toolchain_config_info(
        ctx = ctx,
        toolchain_identifier = "chaquopy_ndk",
        host_system_name = "x86_64-linux-gnu",
        target_system_name = "%{CHAQUOPY_TRIPLET}",
        target_cpu = "%{CHAQUOPY_ABI}",
        target_libc = "unknown",
        compiler = "compiler",
        abi_version = "unknown",
        abi_libc_version = "unknown",
        tool_paths = [
            tool_path(name = name,
                      path = "%{CHAQUOPY_TOOLCHAIN}/bin/%{CHAQUOPY_TRIPLET}-" + name)
             for name in ["ar", "cpp", "dwp", "gcc", "gcov", "ld", "nm", "objcopy", "objdump",
                          "strip"]],
        cxx_builtin_include_directories = [
            "%{CHAQUOPY_TOOLCHAIN}/" + name
            for name in ["include", "lib/gcc", "lib64/clang", "sysroot/usr/include",
                         "sysroot/usr/local/include"]],
    )

cc_toolchain_config = rule(
    implementation = _impl,
    attrs = {},
    provides = [CcToolchainConfigInfo],
)
