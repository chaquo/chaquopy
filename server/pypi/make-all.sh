#!/usr/bin/env bash
set -e

# shellcheck source=/dev/null
. environment.sh

# default values and settings

OPTIONS=""

# parse command line

POSITIONAL=()
while [[ $# -gt 0 ]] ; do
  key="${1}"

  case "${key}" in
    --help)
      echo "Usage: make.sh options

      options
              --package package
              --year year"
      exit 0
      ;;
    --package)
      OPTIONS="${OPTIONS} --package ${2}"
      shift
      shift
      ;;
    --year)
      OPTIONS="${OPTIONS} --year ${2}"
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

# build packages for all python versions

rm -f "${LOGS}/success.log" "${LOGS}/fail.log"
touch "${LOGS}/success.log" "${LOGS}/fail.log"
eval "$(command conda 'shell.bash' 'hook')"

for PYTHON_VERSION in ${PYTHON_VERSIONS}; do
  conda activate "${CONDA_ENV}-${PYTHON_VERSION}"
  ./make.sh ${OPTIONS}
done

echo "Completed successfully."
