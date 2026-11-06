#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
hub=ghcr.io/riccardograssi/photoprism:hub
web=ghcr.io/riccardograssi/photoprism:hub-web
docker build -f "$root/src/Dockerfile" -t "$hub" "$root"
docker push "$hub"
docker build -f "$root/src/web/Dockerfile" -t "$web" "$root"
docker push "$web"
echo "$hub"
echo "$web"
