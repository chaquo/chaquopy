#!/usr/bin/env bash
set -e

# shellcheck source=/dev/null
. environment.sh

# check for package with no output in dist folder

for PACKAGE in ./packages/*; do
  if ! [ -d "${DIST_DIR}/$(basename "${PACKAGE}")" ];then
    echo "- $(basename "${PACKAGE}"): all"
  else
    for PYTHON_VERSION in ${PYTHON_VERSIONS}; do
      if ! [ "$(ls "dist/$(basename "${PACKAGE}")" | grep -c "cp${PYTHON_VERSION/./}")" -ge "4" ]; then
        echo "- $(basename "${PACKAGE}"): ${PYTHON_VERSION}"
      fi
    done
  fi
done
