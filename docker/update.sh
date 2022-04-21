#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"

./versions.sh "$@"
./apply-templates.sh "$@"
