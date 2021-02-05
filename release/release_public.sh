#!/bin/bash
set -e

private_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$private_root"
usage="Usage: release_public.sh OLD_VER NEW_VER"
old_ver=${1:?"$usage"}
new_ver=${2:?"$usage"}

private_src_dir="demo/app/src"

update_version() {
    sed -i -E "s/(com.chaquo.python:gradle):[0-9.]+/\1:${new_ver}/" "$1"
}


echo -n "demo: "
public_root="../public/demo"
update_version "$public_root/build.gradle"
sed -i "s/versionName .*/versionName '${new_ver}'/" "$public_root/app/build.gradle"

public_src_dir="$public_root/app/src"
rm -rf "$public_src_dir/main"
cp -a "$private_src_dir/main" "$public_src_dir"
cp -a $private_src_dir/utils/* "$public_src_dir/main"
cp -a product/runtime/src/test/* "$public_src_dir/main"
echo "done"


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


echo -n "hello: "
cd "$private_root/../public/hello"
git checkout master
git reset --mixed empty-activity
update_version build.gradle
git add app/build.gradle app/src/main/AndroidManifest.xml app/src/main/python/hello.py build.gradle
git rm app/src/main/java/com/chaquo/python/hello/MainActivity.java
git commit -m "Port to Python"
sed -i -E "s|commit/[0-9a-f]+|commit/$(git rev-parse HEAD)|" README.md
git add docs/ISSUE_TEMPLATE.md LICENSE.txt README.md
git commit -m "Add documentation"
git branch "$new_ver"
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
