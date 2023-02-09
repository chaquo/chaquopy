#!/usr/bin/env bash
set -e

CONDA_ENV="beeware"
LOGS="logs"
TOOLCHAINS="support"
CMAKE_VERSION="3.26.0-rc1"
PYTHON_VERSIONS="3.8 3.9 3.10 3.11"
declare -A PYTHON_EXACT_VERSIONS
PYTHON_EXACT_VERSIONS["3.8"]="3.8.16"
PYTHON_EXACT_VERSIONS["3.9"]="3.9.16"
PYTHON_EXACT_VERSIONS["3.10"]="3.10.9"
PYTHON_EXACT_VERSIONS["3.11"]="3.11.0"

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

rm -rf "${LOGS}" "${TOOLCHAINS}"
eval "$(command conda 'shell.bash' 'hook')"
conda activate base

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

mkdir -p "${LOGS}/deps"
conda activate "${CONDA_ENV}-3.10"

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

for PACKAGE in ${PACKAGES}; do
  for PACKAGE_VERSION in $(./versions.py "${PACKAGE}"); do
    sed -i '' "s/version: .*/version: ${PACKAGE_VERSION}/g" "packages/${PACKAGE}/meta.yaml"

    for PYTHON_VERSION in ${PYTHON_VERSIONS}; do
      printf "\n\n*** Building package %s version %s for Python %s ***\n\n" "${PACKAGE}" "${PACKAGE_VERSION}" "${PYTHON_VERSION}"
      conda activate "${CONDA_ENV}-${PYTHON_VERSION}"
      python build-wheel.py --toolchain "${TOOLCHAINS}" --python "${PYTHON_VERSION}" iOS "${PACKAGE}" 2>&1 | tee "${LOGS}/${PYTHON_VERSION}/${PACKAGE}.log"

      # shellcheck disable=SC2010
      if [ "$(ls "dist/${PACKAGE}" | grep -c "cp${PYTHON_VERSION/./}")" -ge "4" ]; then
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
