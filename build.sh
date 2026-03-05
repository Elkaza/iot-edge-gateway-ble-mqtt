#!/bin/sh
set -eu

# build in the same context as start.sh (rootful podman)
if [ "$(id -u)" -ne 0 ]; then
  exec sudo -E "$0" "$@"
fi

UID_TAG="io25m025/ble"

podman build \
  --file Containerfile \
  --tag "$UID_TAG" \
  --tag "localhost/$UID_TAG:latest" \
  .

echo "Built image: $UID_TAG (also tagged localhost/$UID_TAG:latest)"

