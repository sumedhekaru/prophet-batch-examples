#!/bin/sh
# The Cloud Run job image: the local Docker image, built for linux/amd64.
set -e
cd "$(dirname "$0")/../../.."
TAG="${TAG:-prophet-batch-examples/walmart:amd64}" sh walmart_grocery_forecasting/envs/docker/build.sh \
  --platform linux/amd64 "$@"
