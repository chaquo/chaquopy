#!/usr/bin/env bash
set -e

# shellcheck source=/dev/null
. environment.sh

# default values and settings

CMAKE_VERSION="3.26.0-rc1"
declare -A PYTHON_EXACT_VERSIONS
PYTHON_EXACT_VERSIONS["3.8"]="3.8.16"
PYTHON_EXACT_VERSIONS["3.9"]="3.9.16"
PYTHON_EXACT_VERSIONS["3.10"]="3.10.9"
PYTHON_EXACT_VERSIONS["3.11"]="3.11.0"

# setup clean conda environments and toolchains for each Python versions

eval "$(command conda 'shell.bash' 'hook')"
conda activate base

rm -rf "${TOOLCHAINS}"
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

# build docker image for flang

if ! docker info &>/dev/null; then
    echo "Docker daemon not running!"
    exit 1
fi

export DOCKER_DEFAULT_PLATFORM=linux/amd64
DOCKER_BUILDKIT=1 docker build -t flang --compress . $*
docker stop flang &>/dev/null || true
docker rm flang  &>/dev/null || true
docker run -d --name flang -v "$(pwd)/share:/root/host" -v /Users:/Users -v /var/folders:/var/folders -it flang

echo "Completed successfully."
