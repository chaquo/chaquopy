#!/bin/bash -eu
#
# Creates a .tar.gz file containing all the Python code from the given APK. This can be
# unpacked on a device into the directory structure created by standalone-python.sh.

script_name="$(basename $0)"
apk_filename="$(realpath ${1:?})"
abi="${2:?}"
tgz_filename="$(realpath ${3:?})"

apk_dir="$(mktemp -dt $script_name-out.XXXXX)"
unzip -q -d "$apk_dir" "$apk_filename"
cd "$apk_dir/lib/$abi"
python_ver=$(echo libpython*.*.so | sed -E 's/libpython([0-9]+\.[0-9]+).*/\1/')

out_dir="$(mktemp -dt $script_name-apk.XXXXX)"
sp_dir="$out_dir/lib/python$python_ver/site-packages"
mkdir -p "$sp_dir"
cd $apk_dir/assets/chaquopy
for filename in requirements-common.zip requirements-$abi.zip app.zip; do
    # Unzipping an empty ZIP returns a failure status.
    if ! unzip -l "$filename" 2>&1 | grep -q "zipfile is empty"; then
        unzip -q -d "$sp_dir" "$filename"
    fi
done
mv $sp_dir/chaquopy/lib/* "$out_dir/lib"

tar -C "$out_dir" -c . | gzip > "$tgz_filename"
rm -rf "$apk_dir" "$out_dir"
