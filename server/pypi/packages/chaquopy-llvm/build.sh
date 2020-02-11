#!/bin/bash
set -eu

# Based on https://github.com/numba/llvmlite/tree/master/conda-recipes/llvmdev, which,
# according to https://llvmlite.readthedocs.io/en/latest/admin-guide/install.html, "is the
# canonical reference for building LLVM for llvmlite".

# There are undefined symbols in plugin modules, e.g lib/Transforms/Hello.
LDFLAGS=$(echo $LDFLAGS | sed 's/-Wl,--no-undefined//')

triple=$(basename $AR | sed 's/-ar$//')
case $triple in
    arm-linux-androideabi)
        target="ARM"
        ;;
    aarch64-linux-android)
        target="AArch64"
        ;;
    i686-linux-android)
        target="X86"
        ;;
    x86_64-linux-android)
        target="X86"
        ;;
    *)
        echo "Unknown triple '$triple'"
        exit 1
esac

build_tblgen=$(realpath build-tblgen)
if [ ! -e $build_tblgen ]; then  # For rerunning with build-wheel.py --no-unpack.
    $RECIPE_DIR/build-tblgen.sh $build_tblgen
fi

declare -a _cmake_config
_cmake_config+=(-DCMAKE_INSTALL_PREFIX:PATH=${PREFIX})
_cmake_config+=(-DCMAKE_BUILD_TYPE:STRING=Release)
_cmake_config+=(-DLLVM_BUILD_LLVM_DYLIB=ON)
_cmake_config+=(-DLLVM_TABLEGEN=$(realpath $build_tblgen/bin/llvm-tblgen))

_cmake_config+=(-DCMAKE_TOOLCHAIN_FILE="../chaquopy.toolchain.cmake")
_cmake_config+=(-DLLVM_HOST_TRIPLE=$triple)
_cmake_config+=(-DLLVM_TARGETS_TO_BUILD=$target)
_cmake_config+=(-DLLVM_TARGET_ARCH=$target)
_cmake_config+=(-DLLVM_DEFAULT_TARGET_TRIPLE=$triple)

_cmake_config+=(-DLLVM_ENABLE_ASSERTIONS:BOOL=ON)
_cmake_config+=(-DLINK_POLLY_INTO_TOOLS:BOOL=ON)
# Don't really require libxml2. Turn it off explicitly to avoid accidentally linking to system libs
_cmake_config+=(-DLLVM_ENABLE_LIBXML2:BOOL=OFF)
# Urgh, llvm *really* wants to link to ncurses / terminfo and we *really* do not want it to.
_cmake_config+=(-DHAVE_TERMINFO_CURSES=OFF)
# Sometimes these are reported as unused. Whatever.
_cmake_config+=(-DHAVE_TERMINFO_NCURSES=OFF)
_cmake_config+=(-DHAVE_TERMINFO_NCURSESW=OFF)
_cmake_config+=(-DHAVE_TERMINFO_TERMINFO=OFF)
_cmake_config+=(-DHAVE_TERMINFO_TINFO=OFF)
_cmake_config+=(-DHAVE_TERMIOS_H=OFF)
_cmake_config+=(-DCLANG_ENABLE_LIBXML=OFF)
_cmake_config+=(-DLIBOMP_INSTALL_ALIASES=OFF)
_cmake_config+=(-DLLVM_ENABLE_RTTI=OFF)

_cmake_config+=(-DLLVM_BUILD_TOOLS=OFF)  # LLVM_INCLUDE_TOOLS=OFF would disable the shared library.
_cmake_config+=(-DLLVM_INCLUDE_BENCHMARKS=OFF)
_cmake_config+=(-DLLVM_INCLUDE_DOCS=OFF)
_cmake_config+=(-DLLVM_INCLUDE_EXAMPLES=OFF)
_cmake_config+=(-DLLVM_INCLUDE_TESTS=OFF)

mkdir -p build
cd build
rm -f CMakeCache.txt  # For rerunning with build-wheel.py --no-unpack.

cmake -G Ninja "${_cmake_config[@]}" ..
cmake --build . --target install -- -j $(nproc)

cd $PREFIX
rm -r bin share
cd $PREFIX/lib
rm -r *.a cmake
find -type l | xargs rm
for name in *.so; do
    if [[ ! $name =~ ^libLLVM- ]]; then rm $name; fi
done
