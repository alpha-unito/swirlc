#!/bin/bash

ANTLR4_VERSION="4.13.1"

SCRIPT_DIRECTORY=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
SOURCE_DIRECTORY=$(dirname "${SCRIPT_DIRECTORY}")
TMP_DIRECTORY="/tmp/antlr4/parsers"

# Build ANTLR4 Docker
curl -fsSLO "https://raw.githubusercontent.com/antlr/antlr4/${ANTLR4_VERSION}/docker/Dockerfile"
docker build -t antlr4 .
rm -f Dockerfile

# Make tmp destination directory
mkdir -p "${TMP_DIRECTORY}"

# Generate Python parser
docker run                                                \
  --user "${UID}:${GID}"                                  \
  -v "${SOURCE_DIRECTORY}/grammar:/swirl/grammar"         \
  -v "${TMP_DIRECTORY}:/swirl/parsers"                    \
  antlr4                                                  \
  -Dlanguage=Python3                                      \
  -o /swirl/parsers/python                                \
  -visitor                                                \
  /swirl/grammar/SWIRL.g4
mv ${TMP_DIRECTORY}/python/*.py "${SOURCE_DIRECTORY}/swirlc/antlr/"

# Remove tmp destination directory
rm -rf "${TMP_DIRECTORY}"
