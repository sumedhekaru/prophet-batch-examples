#!/bin/sh
# Run all three model variants in the local image (build it first with build.sh). Uses the repo's data/ (downloaded
# into it if missing) and writes results/runs/docker-*. Extra arguments go to pipeline.run, e.g. --n 50.
set -e
cd "$(dirname "$0")/../../.."
mkdir -p data walmart_grocery_forecasting/results/runs
for model in default events events_snap; do
  docker run --rm \
    -v "$PWD/data:/app/data" \
    -v "$PWD/walmart_grocery_forecasting/results/runs:/app/walmart_grocery_forecasting/results/runs" \
    prophet-batch-examples/walmart:local --model "$model" "$@"
done
