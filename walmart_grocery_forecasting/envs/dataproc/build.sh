#!/bin/sh
# Build the Dataproc Serverless image (linux/amd64; PLATFORM overrides it for local tests): pinned requirements +
# prophet-batch from PyPI at the version pinned in uv.lock.
#   TAG=REGION-docker.pkg.dev/PROJECT/REPO/walmart-spark:TAG sh walmart_grocery_forecasting/envs/dataproc/build.sh
# Development: PROPHET_BATCH_LOCAL=../prophet-batch installs a wheel built from that checkout instead of the release.
set -e
cd "$(dirname "$0")/../../.."
BUILD=walmart_grocery_forecasting/envs/dataproc/build
rm -rf "$BUILD" && mkdir -p "$BUILD"
if [ -n "$PROPHET_BATCH_LOCAL" ]; then
  : > "$BUILD/prophet-batch.txt"
  uv build --wheel --out-dir "$BUILD" "$PROPHET_BATCH_LOCAL" > /dev/null 2>&1
  PB_COMMIT="$(git -C "$PROPHET_BATCH_LOCAL" rev-parse --short HEAD)$(git -C "$PROPHET_BATCH_LOCAL" diff --quiet HEAD || echo +dirty)"
else
  uv export --no-default-groups --no-hashes --format requirements.txt | grep '^prophet-batch==' > "$BUILD/prophet-batch.txt"
  PB_COMMIT=
fi
docker build -q --platform "${PLATFORM:-linux/amd64}" -f walmart_grocery_forecasting/envs/dataproc/Dockerfile \
  -t "${TAG:-prophet-batch-examples/walmart-spark:amd64}" \
  --build-arg EXAMPLES_COMMIT="$(git rev-parse --short HEAD)$(git diff --quiet HEAD || echo +dirty)" \
  --build-arg PROPHET_BATCH_COMMIT="$PB_COMMIT" .
