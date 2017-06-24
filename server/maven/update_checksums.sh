#!/bin/bash
set -eu

maven_dir=${1:?"Usage: update_checksums.sh MAVEN-DIR"}

for f in $(find "$maven_dir" -type f -not -name '*.sha1' -not -name '.ht*'); do
    sha1sum "$f" | cut -d' ' -f1 > "$f.sha1"
done
