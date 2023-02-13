#!/usr/bin/env bash
set -e

# default values and settings

CONDA_ENV="beeware"
DIST_DIR="dist"
LOGS="logs"
TOOLCHAINS="support"
CMAKE_VERSION="3.26.0-rc1"
PYTHON_APPLE_SUPPORT="Python-Apple-support"
PYTHON_VERSIONS="3.8 3.9 3.10 3.11"
declare -A PYTHON_EXACT_VERSIONS
PYTHON_EXACT_VERSIONS["3.8"]="3.8.16"
PYTHON_EXACT_VERSIONS["3.9"]="3.9.16"
PYTHON_EXACT_VERSIONS["3.10"]="3.10.9"
PYTHON_EXACT_VERSIONS["3.11"]="3.11.0"
BUILD_DEPS="1"
BUILD_ENVS="1"
YEAR="2021"

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

# packages to build

PACKAGES="
    cffi \
    numpy \
    aiohttp \
    argon2-cffi \
    backports-zoneinfo \
    bcrypt \
    bitarray \
    brotli \
    cryptography \
    cymem \
    cytoolz \
    editdistance \
    ephem \
    frozenlist \
    gensim \
    greenlet \
    kiwisolver \
    lru-dict \
    matplotlib \
    multidict \
    murmurhash \
    netifaces \
    pandas \
    pillow \
    preshed \
    pycrypto \
    pycurl \
    pynacl \
    pysha3 \
    pywavelets \
    pyzbar \
    regex \
    ruamel-yaml-clib \
    scandir \
    spectrum \
    srsly \
    statsmodels \
    twisted \
    typed-ast \
    ujson \
    wordcloud \
    yarl \
    zstandard \
    "
# TODO: to investigate if we need to build those packages for iOS

# blis
# cmake-example
# coincurve
# cvxopt
# dlib
# gevent
# google-crc32c
# grpcio
# h5py
# llvmlite
# lxml
# numba
# opencv-contrib-python
# opencv-contrib-python-headless
# opencv-python
# opencv-python-headless
# psutil
# pycares
# pycryptodome
# pycryptodomex
# python-example
# pyzmq
# rawpy
# rpi-gpio
# scikit-image
# scikit-learn
# scipy
# sentencepiece
# shapely
# soundfile
# spacy
# ta-lib
# tensorflow
# tflite-runtime
# thinc
# tokenizers
# torch
# torchvision
# xgboost

# parse command line

POSITIONAL=()
while [[ $# -gt 0 ]] ; do
  key="${1}"

  case ${key} in
    --help)
      echo "Usage: make.sh options

      options
              --dependency dependency
              --package package
              --skip-deps
              --skip-envs
              --year year"
      exit 0
      ;;
    --dependency)
      DEPENDENCIES=${2}
      shift
      shift
      ;;
    --package)
      PACKAGES=${2}
      shift
      shift
      ;;
    --skip-deps)
      BUILD_DEPS="0"
      shift
      ;;
    --skip-envs)
      BUILD_ENVS="0"
      shift
      ;;
    --year)
      YEAR=${2}
      shift
      shift
      ;;
    *)
      POSITIONAL+=("$1") # save it in an array for later
      shift
    ;;
  esac
done

set -- "${POSITIONAL[@]}" # restore positional parameters

# setup clean conda environments and toolchains for each Python versions

eval "$(command conda 'shell.bash' 'hook')"
conda activate base

if [ "${BUILD_ENVS}" == "1" ]; then
  rm -rf "${LOGS}" "${TOOLCHAINS}"
  curl --silent --location "https://github.com/Kitware/CMake/releases/download/v${CMAKE_VERSION}/cmake-${CMAKE_VERSION}-macos-universal.tar.gz" --output cmake.tar.gz
  mkdir -p "${TOOLCHAINS}"
  tar -xzf cmake.tar.gz --directory "${TOOLCHAINS}"
  mv "${TOOLCHAINS}/cmake-${CMAKE_VERSION}"*/CMake.app "${TOOLCHAINS}"
  rm -rf "${TOOLCHAINS}/cmake-${CMAKE_VERSION}"* cmake.tar.gz

  for PYTHON_VERSION in ${PYTHON_VERSIONS}; do
    rm -rf "$(conda info | grep 'envs directories' | awk -F ':' '{ print $2 }' | sed -e 's/^[[:space:]]*//')/${CONDA_ENV:?}"
    conda create -y --name "${CONDA_ENV}-${PYTHON_VERSION}" "python==${PYTHON_EXACT_VERSIONS[${PYTHON_VERSION}]}"
    conda activate "${CONDA_ENV}-${PYTHON_VERSION}"
    pip3 install -r requirements.txt
    curl --silent --location "$(curl --silent -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" --location https://api.github.com/repos/beeware/Python-Apple-support/releases | grep browser_download_url | grep iOS | grep "${PYTHON_VERSION}" | head -1 | awk '{ print $2 }' | tr -d '"')" --output "python-apple-support-${PYTHON_VERSION}.tar.gz"
    mkdir -p "${TOOLCHAINS}/${PYTHON_VERSION}" "${LOGS}/${PYTHON_VERSION}"
    tar -xzf "python-apple-support-${PYTHON_VERSION}.tar.gz" --directory "${TOOLCHAINS}/${PYTHON_VERSION}"
    rm -rf "python-apple-support-${PYTHON_VERSION}.tar.gz" "${LOGS:?}/${PYTHON_VERSION:?}"/*
  done
fi

# build dependencies

if [ "${BUILD_DEPS}" == "1" ]; then
  mkdir -p "${LOGS}/deps"
  pushd "${TOOLCHAINS}"

  if ! [ -d "${PYTHON_APPLE_SUPPORT}" ]; then
    git clone https://github.com/beeware/Python-Apple-support.git
  fi

  conda activate "${CONDA_ENV}-3.10"
  pushd "${PYTHON_APPLE_SUPPORT}"
  git checkout 3.10
  make libFFI-wheels
  # TODO: make OpenSSL-wheels
  make BZip2-wheels
  make XZ-wheels
  popd
  popd

  mkdir -p "${DIST_DIR}"
  rm -rf "${DIST_DIR}/bzip2" "${DIST_DIR}/libffi" "${DIST_DIR}/xz"
  mv -f "${TOOLCHAINS}/${PYTHON_APPLE_SUPPORT}/wheels/dist"/* "${DIST_DIR}"

  for DEPENDENCY in ${DEPENDENCIES}; do
    printf "\n\n*** Building dependency %s ***\n\n" "${DEPENDENCY}"
    python build-wheel.py --toolchain "${TOOLCHAINS}" --python 3.10 iOS "${DEPENDENCY}" 2>&1 | tee "${LOGS}/deps/${DEPENDENCY}.log"

    # shellcheck disable=SC2010
    if [ "$(ls "dist/${DEPENDENCY}" | grep -c py3)" -ge "2" ]; then
      echo "${DEPENDENCY}" >> "${LOGS}/success.log"
    else
      echo "${DEPENDENCY}" >> "${LOGS}/fail.log"
    fi
  done
fi

# build packages

rm -f "${LOGS}/success.log" "${LOGS}/fail.log"
touch "${LOGS}/success.log" "${LOGS}/fail.log"

for PACKAGE in ${PACKAGES}; do
  PACKAGE_VERSIONS="$(./versions.py "${YEAR}" "${PACKAGE}")"
  printf "\n### Attempting package %s with versions: %s ###\n" "${PACKAGE}" "${PACKAGE_VERSIONS}"

  for PACKAGE_VERSION in ${PACKAGE_VERSIONS}; do
    # TODO: fix this so git don't see a change
    sed -i '' "s/version: .*/version: ${PACKAGE_VERSION}/g" "packages/${PACKAGE}/meta.yaml"

    for PYTHON_VERSION in ${PYTHON_VERSIONS}; do
      printf "\n\n*** Building package %s version %s for Python %s ***\n\n" "${PACKAGE}" "${PACKAGE_VERSION}" "${PYTHON_VERSION}"
      conda activate "${CONDA_ENV}-${PYTHON_VERSION}"
      python build-wheel.py --toolchain "${TOOLCHAINS}" --python "${PYTHON_VERSION}" iOS "${PACKAGE}" 2>&1 | tee "${LOGS}/${PYTHON_VERSION}/${PACKAGE}.log"

      # shellcheck disable=SC2010
      if [ "$(ls "dist/${PACKAGE}" | grep "cp${PYTHON_VERSION/./}" | grep -c "${PACKAGE_VERSION}")" -ge "4" ]; then
        echo "${PACKAGE}-${PACKAGE_VERSION} with Python ${PYTHON_VERSION}" >> "${LOGS}/success.log"
      else
        echo "${PACKAGE}=${PACKAGE_VERSION} with Python ${PYTHON_VERSION}" >> "${LOGS}/fail.log"
      fi
    done
  done
done

echo ""
echo "Packages built successfully:"
cat "${LOGS}/success.log"
echo ""
echo "Packages with errors:"
cat "${LOGS}/fail.log"
echo ""
echo "Completed successfully."
