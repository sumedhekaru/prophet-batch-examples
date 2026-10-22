#!/bin/sh
# Build the local Linux image: runtime requirements pinned from uv.lock, incl. prophet-batch from PyPI.
#   sh walmart_grocery_forecasting/envs/docker/build.sh [extra docker build args, e.g. --platform linux/amd64]
# TAG overrides the image tag (default prophet-batch-examples/walmart:local).
# Development: PROPHET_BATCH_LOCAL=../prophet-batch installs a wheel built from that checkout instead of the release.
set -e
cd "$(dirname "$0")/../../.."
BUILD=walmart_grocery_forecasting/envs/docker/build
rm -rf "$BUILD" && mkdir -p "$BUILD"
if [ -n "$PROPHET_BATCH_LOCAL" ]; then
  uv export --no-default-groups --no-emit-package prophet-batch --no-hashes --format requirements.txt \
    --output-file "$BUILD/requirements.txt" > /dev/null
  uv build --wheel --out-dir "$BUILD" "$PROPHET_BATCH_LOCAL" > /dev/null
  PB_COMMIT="$(git -C "$PROPHET_BATCH_LOCAL" rev-parse --short HEAD)$(git -C "$PROPHET_BATCH_LOCAL" diff --quiet HEAD || echo +dirty)"
else
  uv export --no-default-groups --no-hashes --format requirements.txt --output-file "$BUILD/requirements.txt" > /dev/null
  PB_COMMIT=
fi
docker build -f walmart_grocery_forecasting/envs/docker/Dockerfile -t "${TAG:-prophet-batch-examples/walmart:local}" \
  --build-arg EXAMPLES_COMMIT="$(git rev-parse --short HEAD)$(git diff --quiet HEAD || echo +dirty)" \
  --build-arg PROPHET_BATCH_COMMIT="$PB_COMMIT" \
  "$@" .
