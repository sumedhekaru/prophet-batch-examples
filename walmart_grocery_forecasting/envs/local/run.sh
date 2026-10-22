#!/bin/sh
# Local run: fetch the data, then all three model variants on all 1,437 items (≈ 10 min on a 10-core Mac).
#   sh walmart_grocery_forecasting/envs/local/run.sh            # from the repo root
#   sh walmart_grocery_forecasting/envs/local/run.sh --n 50     # extra arguments go to every run
# prophet-batch is the PyPI release pinned in uv.lock. Development: PROPHET_BATCH_LOCAL=../prophet-batch runs against
# that checkout instead (uv run --with-editable); each run record states which one was used.
set -e
cd "$(dirname "$0")/../../.."
uv run python -m walmart_grocery_forecasting.pipeline.data
for model in default events events_snap; do
  if [ -n "$PROPHET_BATCH_LOCAL" ]; then
    uv run --with-editable "$PROPHET_BATCH_LOCAL" python -m walmart_grocery_forecasting.pipeline.run --env local \
      --model "$model" "$@"
  else
    uv run python -m walmart_grocery_forecasting.pipeline.run --env local --model "$model" "$@"
  fi
done
