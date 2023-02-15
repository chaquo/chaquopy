#!/usr/bin/env bash
set -e

# shellcheck source=/dev/null
. environment.sh

# default values and settings

PYTHON_APPLE_SUPPORT="Python-Apple-support"
PYTHON_VERSION="3.10"

# dependencies to build

DEPENDENCIES="
    chaquopy-freetype \
    chaquopy-libjpeg \
    chaquopy-libogg \
    chaquopy-libpng \
    chaquopy-libxml2 \
    chaquopy-libiconv \
    chaquopy-curl \
    chaquopy-ta-lib \
    chaquopy-zbar \
    "

# TODO: to investigate if we need those dependencies

# chaquopy-crc32c
# chaquopy-flac
# chaquopy-geos
# chaquopy-hdf5
# chaquopy-libcxx
# chaquopy-libffi
# chaquopy-libgfortran
# chaquopy-libomp
# chaquopy-libraw
# chaquopy-libsndfile
# chaquopy-libvorbis
# chaquopy-libxslt
# chaquopy-libzmq
# chaquopy-llvm
# chaquopy-openblas
# chaquopy-secp256k1

# build dependencies

pushd "${TOOLCHAINS}"

if ! [ -d "${PYTHON_APPLE_SUPPORT}" ]; then
  git clone -b "${PYTHON_VERSION}" https://github.com/beeware/Python-Apple-support.git
fi

pushd "${PYTHON_APPLE_SUPPORT}"
make
make libFFI-wheels
make OpenSSL-wheels
make BZip2-wheels
make XZ-wheels
popd
popd

rm -rf "${DIST_DIR}/bzip2" "${DIST_DIR}/libffi" "${DIST_DIR}/openssl" "${DIST_DIR}/xz" "${LOGS}/deps"
mkdir -p "${DIST_DIR}" "${LOGS}/deps"
mv -f "${TOOLCHAINS}/${PYTHON_APPLE_SUPPORT}/wheels/dist"/* "${DIST_DIR}"
rm -f "${LOGS}/success.log" "${LOGS}/fail.log"
touch "${LOGS}/success.log" "${LOGS}/fail.log"

for DEPENDENCY in ${DEPENDENCIES}; do
  printf "\n\n*** Building dependency %s ***\n\n" "${DEPENDENCY}"
  python build-wheel.py --toolchain "${TOOLCHAINS}" --python "${PYTHON_VERSION}" iOS "${DEPENDENCY}" 2>&1 | tee "${LOGS}/deps/${DEPENDENCY}.log"

  # shellcheck disable=SC2010
  if [ "$(ls "dist/${DEPENDENCY}" | grep -c py3)" -ge "2" ]; then
    echo "${DEPENDENCY}" >> "${LOGS}/success.log"
  else
    echo "${DEPENDENCY}" >> "${LOGS}/fail.log"
  fi
done

echo ""
echo "Packages built successfully:"
cat "${LOGS}/success.log"
echo ""
echo "Packages with errors:"
cat "${LOGS}/fail.log"
echo ""
echo "Completed successfully."
