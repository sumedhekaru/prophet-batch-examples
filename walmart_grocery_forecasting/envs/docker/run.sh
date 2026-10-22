#!/bin/sh
# Run all three model variants in the local image (build it first with build.sh). Uses the repo's data/ (downloaded
# into it if missing) and writes results/runs/docker-*. Extra arguments go to pipeline.run, e.g. --n 50.
# REPS=3: benchmark, 3 repetitions into results/runs/docker-bench-<stamp>/ + summary.md (pipeline/bench_summary.py).
set -e
cd "$(dirname "$0")/../../.."
MODELS="${MODELS:-default events events_snap}"
mkdir -p data walmart_grocery_forecasting/results/runs
SUB=
if [ -n "$REPS" ]; then
  SUB=docker-bench-$(date +%Y%m%d-%H%M%S)
  set -- --out "/app/walmart_grocery_forecasting/results/runs/$SUB" "$@"
fi
rep=1
while [ "$rep" -le "${REPS:-1}" ]; do
  for model in $MODELS; do
    docker run --rm \
      -v "$PWD/data:/app/data" \
      -v "$PWD/walmart_grocery_forecasting/results/runs:/app/walmart_grocery_forecasting/results/runs" \
      "${TAG:-prophet-batch-examples/walmart:local}" --model "$model" "$@"
  done
  rep=$((rep + 1))
done
if [ -n "$REPS" ]; then
  OUT=walmart_grocery_forecasting/results/runs/$SUB
  uv run python -m walmart_grocery_forecasting.pipeline.bench_summary "$OUT" > "$OUT/summary.md"
  echo "summary: $OUT/summary.md"
fi
