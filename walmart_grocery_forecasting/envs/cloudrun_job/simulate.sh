#!/bin/sh
# Simulate the Cloud Run job locally: a local directory stands in for the Cloud Storage bucket, mounted at the same
# path as the job's volume. On Apple Silicon the amd64 image runs under emulation: check behaviour, don't time it.
#   sh walmart_grocery_forecasting/envs/cloudrun_job/simulate.sh --n 20 --serial-n 4
set -e
cd "$(dirname "$0")/../../.."
BUCKET_DIR="${BUCKET_DIR:-$PWD/data/fake-bucket}"
mkdir -p "$BUCKET_DIR/data"
[ -f "$BUCKET_DIR/data/m5/m5.zip" ] || { mkdir -p "$BUCKET_DIR/data/m5"; cp data/m5/m5.zip "$BUCKET_DIR/data/m5/" 2>/dev/null || true; }
docker run --rm --platform linux/amd64 --cpus "${CPUS:-8}" \
  -v "$BUCKET_DIR:/mnt/gcs" \
  -e DATA_DIR=/mnt/gcs/data/m5 -e OUT_DIR=/mnt/gcs/results -e RUN_ENV=cloudrun-sim \
  "${TAG:-prophet-batch-examples/walmart:amd64}" "$@"
