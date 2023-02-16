#!/usr/bin/env bash

cd /root/host || exit
cd "${1}" || exit
flang "${@:2}"
