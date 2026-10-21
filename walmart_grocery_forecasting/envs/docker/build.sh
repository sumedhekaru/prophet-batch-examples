#!/bin/sh
# Build the local Linux image: pinned runtime requirements from uv.lock + a prophet-batch wheel from ../prophet-batch.
#   sh walmart_grocery_forecasting/envs/docker/build.sh [extra docker build args, e.g. --platform linux/amd64]
# TAG overrides the image tag (default prophet-batch-examples/walmart:local).
set -e
cd "$(dirname "$0")/../../.."
BUILD=walmart_grocery_forecasting/envs/docker/build
rm -rf "$BUILD" && mkdir -p "$BUILD"
uv export --no-default-groups --no-emit-package prophet-batch --no-hashes --format requirements.txt \
  --output-file "$BUILD/requirements.txt" > /dev/null
uv build --wheel --out-dir "$BUILD" ../prophet-batch > /dev/null
docker build -f walmart_grocery_forecasting/envs/docker/Dockerfile -t "${TAG:-prophet-batch-examples/walmart:local}" \
  --build-arg EXAMPLES_COMMIT="$(git rev-parse --short HEAD)$(git diff --quiet HEAD || echo +dirty)" \
  --build-arg PROPHET_BATCH_COMMIT="$(git -C ../prophet-batch rev-parse --short HEAD)" \
  "$@" .
