#!/bin/bash

ANTLR4_VERSION="4.13.2"

SCRIPT_DIRECTORY=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
SOURCE_DIRECTORY=$(dirname "${SCRIPT_DIRECTORY}")
TMP_DIRECTORY=$(mktemp -d)
trap 'rm -rf "${TMP_DIRECTORY}" Dockerfile' EXIT

# Build ANTLR4 Docker
curl -fsSLo Dockerfile "https://raw.githubusercontent.com/antlr/antlr4/${ANTLR4_VERSION}/docker/Dockerfile"
docker build -t antlr4 .

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
for generated in "${TMP_DIRECTORY}"/python/*.py; do
  cmp -s "${generated}" "${SOURCE_DIRECTORY}/swirlc/antlr/$(basename "${generated}")" || \
    mv "${generated}" "${SOURCE_DIRECTORY}/swirlc/antlr/"
done
