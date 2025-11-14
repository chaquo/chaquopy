#!/bin/bash
set -eu

maven_dir="$(realpath "$(dirname $0)/../maven")"
tmp_dir="$maven_dir/bundle-$(date +%Y%m%d.%H%M%S)"
mkdir "$tmp_dir"
trap 'rm -r "$tmp_dir"' EXIT

for version_dir in "$@"; do
    # Each argument must be a relative path within `maven`.
    cd "$maven_dir"
    if [ ! -e "$(pwd)/$version_dir" ]; then
        echo "$version_dir does not exist within $(pwd)"
        exit 1
    fi

    version_dir_out="$tmp_dir/$version_dir"
    mkdir -p "$(dirname "$version_dir_out")"
    cp -a "$version_dir" "$version_dir_out"

    # Create hashes and signatures.
    cd "$version_dir_out"
    rm -f *.md5 *.sha* *.asc
    for name in *; do
        for hash in md5 sha1; do
            "${hash}sum" "$name" | cut -d " " -f 1 > "$name.$hash"
        done
        gpg -abv $name
    done
done

cd "$tmp_dir"
zip -qr "$tmp_dir.zip" *
echo "Created $tmp_dir.zip"
