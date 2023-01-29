#!/bin/bash
set -e

private_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$private_root"
usage="Usage: release_public.sh OLD_VER NEW_VER"
old_ver=${1:?"$usage"}
new_ver=${2:?"$usage"}

private_src_dir="demo/app/src"

update_version() {
    # We can't use `sed -i` with no argument, because macOS and Linux handle that in
    # incompatible ways.
    sed -i.original -E "s/(com.chaquo.python.+version ')[0-9.]+/\1${new_ver}/" "$1"
    rm "$1.original"
}


echo -n "console: "
public_root="../public/console"
update_version "$public_root/build.gradle"

private_utils_dir="$private_src_dir/utils"
public_main_dir="$public_root/app/src/main"
for pattern in "java/com/chaquo/python/utils/"{*ConsoleActivity,*LiveEvent,Utils}".java" \
               "python/chaquopy/__init__.py" "python/chaquopy/utils/"{__init__,console}".py" \
               "res/drawable*/ic_vertical_align_*" "res/layout*/activity_console.xml" \
               "res/menu*/top_bottom.xml" "res/values*/console.xml" ; do
    for private_file in $private_utils_dir/$pattern; do
        public_file="$(echo "$private_file" | sed "s|$private_utils_dir|$public_main_dir|")"
        rm -rf "$public_file"
        mkdir -p "$(dirname "$public_file")"
        cp -a "$private_file" "$public_file"
    done
done
echo "done"


echo -n "matplotlib: "
public_root="../public/matplotlib"
update_version "$public_root/build.gradle"
echo "done"


echo "If there are files listed below, they may require manual merging."
echo "Run 'git diff $old_ver -- <filename>' to check."
echo "If too many files are listed, this is probably because of end-of-line issues: "
echo "run this script a second time and it should give the correct output."
cd "$private_root"
git diff --name-status "$old_ver" -- demo | grep -v "$private_src_dir"
