#!/bin/sh
# The Cloud Run job image: the local Docker image of public_datasets, built for linux/amd64.
set -e
cd "$(dirname "$0")/../../.."
TAG="${TAG:-prophet-batch-examples/public-datasets:amd64}" sh public_datasets/envs/docker/build.sh \
  --platform linux/amd64 "$@"
