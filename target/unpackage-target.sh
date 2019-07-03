#/bin/bash
#
# Positional arguments:
#  * Path to Crystax NDK
#  * Maven repository URL, e.g. "https://chaquo.com/maven/com/chaquo/python/target/3.6.5-11"

set -eu

crystax_dir="$(cd ${1:?} && pwd)"
maven_url="${2:?}"
full_ver="$(basename $maven_url)"
short_ver="$(echo $full_ver | sed -E 's/^([0-9]+\.[0-9]+).*/\1/')"

crystax_python_dir="$crystax_dir/sources/python/$short_ver"
mkdir "$crystax_python_dir"  # Error if already exists: don't want to overwrite it.

tmp_dir="/tmp/unpackage-target-$$"
mkdir "$tmp_dir"

for abi in armeabi-v7a arm64-v8a x86 x86_64; do
    abi_dir="$tmp_dir/$abi"
    mkdir "$abi_dir"
    filename="target-$full_ver-$abi.zip"
    wget -P "$abi_dir" "$maven_url/$filename"
    unzip -q -d "$abi_dir" "$abi_dir/$filename"

    # Include directory is the same for all ABIs.
    if [[ ! -e "$crystax_python_dir/include" ]]; then
        cp -a "$abi_dir/include" "$crystax_python_dir"
    fi

    mkdir -p "$crystax_python_dir/libs/$abi"
    cp "$abi_dir/jniLibs/$abi/libpython${short_ver}m.so" "$crystax_python_dir/libs/$abi"
done

rm -rf "$tmp_dir"
