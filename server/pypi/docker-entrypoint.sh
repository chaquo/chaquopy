#!/bin/bash
set -eu

exec pypi/build-wheel.py --toolchain $toolchain "$@"
