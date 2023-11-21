#!/bin/bash
set -eu

version="${1:?}"

cd "$(dirname $(realpath $0))/../maven"

find . -name $version | while read dir; do (
    cd $dir

    # Maven Central adds hashes to every file in the bundle, even existing hash files.
    rm -f *.md5 *.sha*

    for name in *; do
        if ! echo $name | grep -Eq '\.(md5|sha|asc)'; then
            gpg -abv $name
        fi
    done

    jar -cvf ../$version.jar *
) done
