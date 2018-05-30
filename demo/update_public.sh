#!/bin/bash
set -e

cd "$(dirname "$0")/.."
since_commit=${1:?"Usage: update_public.sh <since-commit>"}


echo -n "demo: "
private_src_dir="demo/app/src"
public_src_dir="../public/demo/app/src"
for source_set in main two three; do
    rm -rf "$public_src_dir/$source_set"
    cp -a "$private_src_dir/$source_set" "$public_src_dir"
done
cp -a product/runtime/src/test/* "$public_src_dir/main"
echo "done"


echo -n "console: "
private_main_dir="$private_src_dir/main"
public_src_dir="../public/console/app/src"
public_main_dir="$public_src_dir/main"
for pattern in "java/com/chaquo/python/utils" \
               "python/chaquopy/__init__.py" "python/chaquopy/utils" \
               "res/drawable*/ic_vertical_align_*" "res/layout*/activity_console.xml" \
               "res/menu*/top_bottom.xml" "res/values*/console.xml" ; do
    for private_file in $private_main_dir/$pattern; do
        public_file="$(echo "$private_file" | sed "s|$private_main_dir|$public_main_dir|")"
        rm -rf "$public_file"
        mkdir -p "$(dirname "$public_file")"
        cp -a "$private_file" "$public_file"
    done
done

public_test_dir="$public_src_dir/test"
rm -rf "$public_test_dir"
cp -a "$private_src_dir/test" "$public_test_dir"
echo "done"


echo "If there are files listed below, they may require manual merging."
echo "Run 'git diff $since_commit -- <filename>' to check."
echo "If too many files are listed, this is probably because of end-of-line issues: "
echo "run this script a second time and it should give the correct output."
git diff --name-status "$since_commit" -- demo | grep -v "$private_src_dir"
