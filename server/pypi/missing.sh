#!/usr/bin/env bash
set -e

# shellcheck source=/dev/null
. environment.sh

# check for package with no output in dist folder

for PACKAGE in ./packages/*; do
  if ! [ -d "${DIST_DIR}/$(basename ${PACKAGE})" ];then
    echo "$(basename ${PACKAGE})"
  fi
done
