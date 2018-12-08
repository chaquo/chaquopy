# Chaquopy: this file is based on
# https://github.com/bazelbuild/bazel/blob/0.16.1/tools/cpp/CROSSTOOL, specifically, the
# local_linux toolchain.

# Chaquopy: Compulsory but unused.
major_version: ""
minor_version: ""
default_target_cpu: ""

default_toolchain {
  cpu: "chaquopy"
  toolchain_identifier: "chaquopy_ndk"
}

toolchain {
  abi_version: "local"
  abi_libc_version: "local"
  builtin_sysroot: ""
  compiler: "compiler"
  host_system_name: "local"
  needsPic: true
  supports_gold_linker: false
  supports_incremental_linker: false
  supports_fission: false
  supports_interface_shared_objects: false
  supports_normalizing_ar: false
  supports_start_end_lib: false
  target_libc: "local"
  target_cpu: "chaquopy"
  target_system_name: "local"
  toolchain_identifier: "chaquopy_ndk"

  tool_path { name: "ar" path: "%{CHAQUOPY_TOOL_PREFIX}ar" }
  tool_path { name: "compat-ld" path: "%{CHAQUOPY_TOOL_PREFIX}ld" }
  tool_path { name: "cpp" path: "%{CHAQUOPY_TOOL_PREFIX}cpp" }
  tool_path { name: "dwp" path: "%{CHAQUOPY_TOOL_PREFIX}dwp" }
  tool_path { name: "gcc" path: "%{CHAQUOPY_TOOL_PREFIX}gcc" }
  cxx_flag: "-std=c++0x"
  linker_flag: "-lstdc++"

  cxx_builtin_include_directory: "%{CHAQUOPY_TOOLCHAIN}/include"
  cxx_builtin_include_directory: "%{CHAQUOPY_TOOLCHAIN}/lib/gcc"
  cxx_builtin_include_directory: "%{CHAQUOPY_TOOLCHAIN}/lib64/clang"
  cxx_builtin_include_directory: "%{CHAQUOPY_TOOLCHAIN}/sysroot/usr/include"

  tool_path { name: "gcov" path: "%{CHAQUOPY_TOOL_PREFIX}gcov" }

  # C(++) compiles invoke the compiler (as that is the one knowing where
  # to find libraries), but we provide LD so other rules can invoke the linker.
  tool_path { name: "ld" path: "%{CHAQUOPY_TOOL_PREFIX}ld" }

  tool_path { name: "nm" path: "%{CHAQUOPY_TOOL_PREFIX}nm" }
  tool_path { name: "objcopy" path: "%{CHAQUOPY_TOOL_PREFIX}objcopy" }
  objcopy_embed_flag: "-I"
  objcopy_embed_flag: "binary"
  tool_path { name: "objdump" path: "%{CHAQUOPY_TOOL_PREFIX}objdump" }
  tool_path { name: "strip" path: "%{CHAQUOPY_TOOL_PREFIX}strip" }

  # Chaquopy: disabled these: they're not supported by Clang in NDK r18.
  #
  # Anticipated future default.
  # unfiltered_cxx_flag: "-no-canonical-prefixes"
  # unfiltered_cxx_flag: "-fno-canonical-system-headers"

  # Make C++ compilation deterministic. Use linkstamping instead of these
  # compiler symbols.
  unfiltered_cxx_flag: "-Wno-builtin-macro-redefined"
  unfiltered_cxx_flag: "-D__DATE__=\"redacted\""
  unfiltered_cxx_flag: "-D__TIMESTAMP__=\"redacted\""
  unfiltered_cxx_flag: "-D__TIME__=\"redacted\""

  # Security hardening on by default.
  # Conservative choice; -D_FORTIFY_SOURCE=2 may be unsafe in some cases.
  # We need to undef it before redefining it as some distributions now have
  # it enabled by default.
  compiler_flag: "-U_FORTIFY_SOURCE"
  compiler_flag: "-D_FORTIFY_SOURCE=1"
  compiler_flag: "-fstack-protector"
  linker_flag: "-Wl,-z,relro,-z,now"

  # Enable coloring even if there's no attached terminal. Bazel removes the
  # escape sequences if --nocolor is specified. This isn't supported by gcc
  # on Ubuntu 14.04.
  # compiler_flag: "-fcolor-diagnostics"

  # All warnings are enabled. Maybe enable -Werror as well?
  compiler_flag: "-Wall"

  # Chaquopy: disabled these: they're not supported by Clang in NDK r18.
  #
  # Enable a few more warnings that aren't part of -Wall.
  # compiler_flag: "-Wunused-but-set-parameter"
  # But disable some that are problematic.
  # compiler_flag: "-Wno-free-nonheap-object" # has false positives

  # Keep stack frames for debugging, even in opt mode.
  compiler_flag: "-fno-omit-frame-pointer"

  %{CHAQUOPY_COMPILER_FLAGS}

  # Chaquopy: disabled these: they're not supported by Clang in NDK r18.
  #
  # Anticipated future default.
  # linker_flag: "-no-canonical-prefixes"
  # Have gcc return the exit code from ld.
  # linker_flag: "-pass-exit-codes"

  # Gold linker only? Can we enable this by default?
  # linker_flag: "-Wl,--warn-execstack"
  # linker_flag: "-Wl,--detect-odr-violations"

  %{CHAQUOPY_LINKER_FLAGS}

  compilation_mode_flags {
    mode: DBG
    # Enable debug symbols.
    compiler_flag: "-g"
  }
  compilation_mode_flags {
    mode: OPT

    # No debug symbols.
    # Maybe we should enable https://gcc.gnu.org/wiki/DebugFission for opt or
    # even generally? However, that can't happen here, as it requires special
    # handling in Bazel.
    compiler_flag: "-g0"

    # Conservative choice for -O
    # -O3 can increase binary size and even slow down the resulting binaries.
    # Profile first and / or use FDO if you need better performance than this.
    compiler_flag: "-O2"

    # Disable assertions
    compiler_flag: "-DNDEBUG"

    # Removal of unused code and data at link time (can this increase binary size in some cases?).
    #
    # Chaquopy: disabled all of these: on ARMv7 with GCC 4.9, -fdata-sections causes a "section
    # type conflict" error when compiling the C++11 thread_local keyword, e.g. in
    # tensorflow/core/util/work_sharder.cc.
    #
    # compiler_flag: "-ffunction-sections"
    # compiler_flag: "-fdata-sections"
    # linker_flag: "-Wl,--gc-sections"
  }
  linking_mode_flags { mode: DYNAMIC }
}
