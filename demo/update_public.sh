#!/bin/bash
set -e

since_commit=${1:?"Usage: update_public.sh <since-commit>"}

cd "$(dirname "$0")/.."
private_src_dir="demo/app/src"
public_src_dir="../public/demo/app/src"
rm -rf "$public_src_dir"
cp -a "$private_src_dir" "$public_src_dir"
cp -a product/runtime/src/test/* "$public_src_dir/main"
echo "Source code copied."

echo "If there are files listed below, they may require manual merging:"
git diff --name-status "$since_commit" -- demo | grep -v "$private_src_dir"
echo "Run 'git diff $since_commit -- <filename>' to check"
