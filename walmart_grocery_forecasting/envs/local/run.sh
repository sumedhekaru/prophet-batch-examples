#!/bin/sh
# Local run: fetch the data, then all three model variants on all 1,437 items (≈ 10 min on a 10-core Mac).
#   sh walmart_grocery_forecasting/envs/local/run.sh            # from the repo root
#   sh walmart_grocery_forecasting/envs/local/run.sh --n 50     # extra arguments go to every run
#   REPS=3 sh walmart_grocery_forecasting/envs/local/run.sh     # benchmark: 3 repetitions into results/runs/local-bench-<stamp>/
#                                                               # + summary.md (examples_core/bench_summary.py)
# prophet-batch is the PyPI release pinned in uv.lock. Development: PROPHET_BATCH_LOCAL=../prophet-batch runs against
# that checkout instead (uv run --with-editable); each run record states which one was used.
set -e
cd "$(dirname "$0")/../../.."
MODELS="${MODELS:-default events events_snap}"
uv run python -m walmart_grocery_forecasting.pipeline.data
if [ -n "$REPS" ]; then
  OUT=walmart_grocery_forecasting/results/runs/local-bench-$(date +%Y%m%d-%H%M%S)
  set -- --out "$OUT" "$@"
fi
run() {
  if [ -n "$PROPHET_BATCH_LOCAL" ]; then
    uv run --with-editable "$PROPHET_BATCH_LOCAL" python -m walmart_grocery_forecasting.pipeline.run --env local "$@"
  else
    uv run python -m walmart_grocery_forecasting.pipeline.run --env local "$@"
  fi
}
rep=1
while [ "$rep" -le "${REPS:-1}" ]; do
  for model in $MODELS; do run --model "$model" "$@"; done
  rep=$((rep + 1))
done
if [ -n "$REPS" ]; then
  uv run python -m examples_core.bench_summary "$OUT" > "$OUT/summary.md"
  echo "summary: $OUT/summary.md"
fi
