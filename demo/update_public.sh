#!/bin/bash
set -e

since_commit=${1:?"Usage: update_public.sh <since-commit>"}

cd "$(dirname "$0")/.."
public_main_dir="../public/demo/app/src/main"
rm -rf "$public_main_dir"
mkdir "$public_main_dir"
cp -a demo/app/src/main/* "$public_main_dir"
cp -a product/runtime/src/test/* "$public_main_dir"
echo "Source code copied."

echo "If there are any files which require manual merging, they are listed below:"
git diff --name-status "$since_commit" -- demo | grep -v "demo/app/src/main"
