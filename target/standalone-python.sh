#!/bin/bash -eu
#
# Creates a .tar.gz file containing Python and supporting libraries from the given toolchain.
# Unpack this on a device, set LD_LIBRARY_PATH to include the `lib` subdirectory, and you'll
# then be able to run the Python interpreter in the `bin` subdirectory.

script_name="$(basename $0)"
toolchain_dir="$(realpath ${1:?})"
tgz_filename="$(realpath ${2:?})"

out_dir="$(mktemp -dt $script_name-out.XXXXX)"
mkdir "$out_dir/lib"
cp -a $toolchain_dir/sysroot/usr/lib/lib{python,crypto,ssl,sqlite}*.so* "$out_dir/lib"
cd "$out_dir/lib"
python_ver=$(echo libpython*.*.so | sed -E 's/libpython([0-9]+\.[0-9]+).*/\1/')
python_ver_major=$(echo "$python_ver" | sed -E 's/^([0-9]+)\..*/\1/')

cp -a "$toolchain_dir/sysroot/usr/lib/python$python_ver" "$out_dir/lib"
cd "$out_dir/lib/python$python_ver"
find -name __pycache__ | xargs rm -r

cd "$out_dir/lib"
chmod u+w $(find -name "*.so")
$toolchain_dir/*/bin/strip $(find -name "*.so")

mkdir "$out_dir/bin"
# Some versions of Android block hard links using SELinux, so make sure we only use symlinks.
cp "$toolchain_dir/sysroot/usr/bin/python$python_ver" "$out_dir/bin"
ln -s "python$python_ver" "$out_dir/bin/python"
ln -s "python$python_ver" "$out_dir/bin/python$python_ver_major"

tar -C "$out_dir" -c . | gzip > "$tgz_filename"
rm -rf "$out_dir"
