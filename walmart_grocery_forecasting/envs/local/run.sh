#!/bin/sh
# Local run: fetch the data, then all three model variants on all 1,437 items (≈ 10 min on a 10-core Mac).
#   sh walmart_grocery_forecasting/envs/local/run.sh            # from the repo root
#   sh walmart_grocery_forecasting/envs/local/run.sh --n 50     # extra arguments go to every run
set -e
cd "$(dirname "$0")/../../.."
uv run python -m walmart_grocery_forecasting.pipeline.data
for model in default events events_snap; do
  uv run python -m walmart_grocery_forecasting.pipeline.run --env local --model "$model" "$@"
done
