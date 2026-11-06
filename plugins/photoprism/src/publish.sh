#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
custom=ghcr.io/riccardograssi/photoprism:hub
docker build -f "$root/src/Dockerfile" -t "$custom" "$root"
docker push "$custom"
echo "$custom"
