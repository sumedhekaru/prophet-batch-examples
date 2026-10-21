#!/bin/sh
# Build the Dataproc Serverless image (linux/amd64; PLATFORM overrides it for local tests): pinned requirements + a prophet-batch wheel from ../prophet-batch.
#   TAG=REGION-docker.pkg.dev/PROJECT/REPO/walmart-spark:TAG sh walmart_grocery_forecasting/envs/dataproc/build.sh
set -e
cd "$(dirname "$0")/../../.."
BUILD=walmart_grocery_forecasting/envs/dataproc/build
rm -rf "$BUILD" && mkdir -p "$BUILD"
uv build --wheel --out-dir "$BUILD" ../prophet-batch > /dev/null 2>&1
docker build -q --platform "${PLATFORM:-linux/amd64}" -f walmart_grocery_forecasting/envs/dataproc/Dockerfile \
  -t "${TAG:-prophet-batch-examples/walmart-spark:amd64}" \
  --build-arg EXAMPLES_COMMIT="$(git rev-parse --short HEAD)$(git diff --quiet HEAD || echo +dirty)" \
  --build-arg PROPHET_BATCH_COMMIT="$(git -C ../prophet-batch rev-parse --short HEAD)" .
