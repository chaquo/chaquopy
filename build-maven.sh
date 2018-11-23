#!/bin/bash
set -eu

license_mode=${1:-}

cd $(dirname $0)
docker build -t chaquopy-target target
docker build -t chaquopy --build-arg license_mode=$license_mode .

container_name="chaquopy-$(date +%s)"
docker run --name $container_name chaquopy
docker cp $container_name:/root/maven .
docker rm $container_name
