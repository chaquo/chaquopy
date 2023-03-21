This file explains how to build the cryptography 39 wheels for Python 3.10 (chaquopy 14.0.2).

See also https://github.com/chaquo/chaquopy/issues/657 for an overview and old instructions.

The new chaquopy version extends the compatibility to Python 3.10 and Python 3.11.
W.r.t. the old instrucitons, there are some changes made in the toolchain, mainly:

 - 217ada59d3ac2e592c48dd1fbd6598f9b6bb4a75  - Increase minimum API level to 21
 - 73d79a3218421de5648cc1a852106e7ee4f484c6 - Update build-wheel for new toolchain arrangement
 - now that chaquopy is opensource, the old build-wheel repository has been merged to the main chaquopy repo

NOTE: armv7 is currently not working properly

## Preparing the build environment

The following instructions are meant for archlinux. It's also highly recommended to create a fakeroot environment to avoid polluting the build machine (refer to the old instructions).

```
yay -S patchelf miniconda3
```

```
# clone repo
cd ~/src/
git clone https://github.com/emanuele-f/chaquopy
cd chaquopy
git checkout cryptography-wheel
mkdir build

# install python env and requirements
source /opt/miniconda3/etc/profile.d/conda.sh
conda create -n build-wheel python=3.10
conda activate build-wheel
pip install -r server/pypi/requirements.txt

# pip 19.3 from /opt/miniconda3/envs/build-wheel/lib/python3.10/site-packages/pip (python 3.10)
pip --version

# Python 3.10.9
python --version

# download target Python version
cd ~/chaquopy
mkdir -p maven/com/chaquo/python/target/3.10.6-1-1
cd maven/com/chaquo/python/target/3.10.6-1-1
wget https://repo.maven.apache.org/maven2/com/chaquo/python/target/3.10.6-1/target-3.10.6-1-x86_64.zip
wget https://repo.maven.apache.org/maven2/com/chaquo/python/target/3.10.6-1/target-3.10.6-1-arm64-v8a.zip
wget https://repo.maven.apache.org/maven2/com/chaquo/python/target/3.10.6-1/target-3.10.6-1-armeabi-v7a.zip
wget https://repo.maven.apache.org/maven2/com/chaquo/python/target/3.10.6-1/target-3.10.6-1-x86.zip
```

Set up the Android command line tools as explained at server/pypi/README.md (required to download the ndk versions later)

- Currently: https://dl.google.com/android/repository/commandlinetools-linux-9477386_latest.zip

Install Rust `1.60.0`. NOTE: latest rust version fails with `ld: error: unable to find library -lunwind` during the build.

```
pacman -Rs rustup rust
curl https://sh.rustup.rs -sSf | sh -s -- -y -t 1.60.0
source "$HOME/.cargo/env"

# required for cross-compilation
rustup target add aarch64-linux-android
rustup target add arm-linux-androideabi
rustup target add i686-linux-android
rustup target add x86_64-linux-android

# Verify installed cross-compilation libraries
rustc --print target-list | grep android
```

## Env setup

```
# only necessary on subsequent builds
source "$HOME/.cargo/env"
source /opt/miniconda3/etc/profile.d/conda.sh
conda activate build-wheel

# target python version
version=3.10.6

# must match info specified in target/build-common.sh
api_level=21
ndk_version=22.1.7171670

TOOLCHAIN="$ANDROID_HOME/ndk/$ndk_version/toolchains/llvm/prebuilt/linux-x86_64"
```

All the step below must be performed for each ABI to build

## ABI selection

```
# only pick the target ABI of choice
ARCH="x86"         CPU="x86"     TOOL_PREFIX="i686-linux-android"    CLANG_TRIPLET="" 
ARCH="armeabi-v7a" CPU="arm"     TOOL_PREFIX="arm-linux-androideabi" CLANG_TRIPLET="armv7a-linux-androideabi"
ARCH="arm64-v8a"   CPU="aarch64" TOOL_PREFIX="aarch64-linux-android" CLANG_TRIPLET=""
ARCH="x86_64"      CPU="x86_64"  TOOL_PREFIX="x86_64-linux-android"  CLANG_TRIPLET=""

cd ~/src/chaquopy/build
SYSROOT=`readlink -f $ARCH/sysroot`
```

## Python cross-compilation

This step is required only once per ABI. You can skip this for subsequent wheels build.

```
rm -rf $ARCH/sysroot/usr $ARCH/Python-$version
mkdir -p $ARCH/sysroot/usr/lib $ARCH/sysroot/usr/include
tar -C $ARCH -xf Python-$version.tgz

cp $TOOLCHAIN/sysroot/usr/lib/${TOOL_PREFIX}/*.a $SYSROOT/usr/lib
cp -r $TOOLCHAIN/sysroot/usr/lib/${TOOL_PREFIX}/${api_level}/* $SYSROOT/usr/lib
cp -r $TOOLCHAIN/sysroot/usr/include/* $SYSROOT/usr/include

export CC=$TOOLCHAIN/bin/${CLANG_TRIPLET:-$TOOL_PREFIX}${api_level}-clang
export CXX=${CC}++
export AR=$TOOLCHAIN/bin/llvm-ar
export AS=$TOOLCHAIN/bin/$TOOL_PREFIX-as
export LD=$TOOLCHAIN/bin/ld
export LDSHARED="$CC -shared"
export RANLIB="$TOOLCHAIN/bin/llvm-ranlib"
export STRIP="$TOOLCHAIN/bin/llvm-strip"
export NM="$TOOLCHAIN/bin/llvm-nm"
export READELF="$TOOLCHAIN/bin/llvm-readelf"
export CFLAGS="-fPIC -DANDROID --sysroot=$SYSROOT"
export CXXFLAGS="$CFLAGS"
export LD_FLAGS="--sysroot=$SYSROOT -Wl,--exclude-libs,libgcc.a -Wl,--exclude-libs,libgcc_real.a -Wl,--exclude-libs,libunwind.a -Wl,--build-id=sha1 -Wl,--no-rosegment -lm -Wl,--no-undefined"

cd $ARCH/Python-$version
./configure --build=x86_64-unknown-linux-gnu --host=$CPU-linux-android --enable-shared --prefix=`readlink -f ../sysroot/usr` \
    ac_cv_file__dev_ptmx=no ac_cv_file__dev_ptc=no ac_cv_have_long_long_format=yes ac_cv_buggy_getaddrinfo=no

# build (ignore errors, they occur because of missing dependencies, but we are only interested in libpython and related _sysconfigdata)
make -j $(nproc)
make install

# Patch SONAME to correspond to the chaquopy "libpython3.10.so"
# Verify with x86_64-linux-android-readelf -Wa $SYSROOT/usr/lib/libpython3.10.so | grep SONAME
mv $SYSROOT/usr/lib/libpython3.10.so{.1.0,}
patchelf --set-soname libpython3.10.so $SYSROOT/usr/lib/libpython3.10.so
```

## Build cryptography

```
cd ~/src/chaquopy/server/pypi
./build-wheel.py --python 3.10 --abi $ARCH cryptography
```


## Known issues

- On arm7, importing the wheel at runtime throws `ImportError: dlopen failed: cannot locate symbol "decode_eht_entry"`
- Cryptography "legacy" ciphers are disabled (as if `CRYPTOGRAPHY_OPENSSL_NO_LEGACY` were defined)
