#!/bin/sh
# Local run of the public datasets: fetch the data, then each dataset (default: the three large ones).
#   sh public_datasets/envs/local/run.sh                                  # from the repo root
#   DATASETS="m4_weekly m4_hourly tourism_monthly" sh public_datasets/envs/local/run.sh
#   REPS=3 sh public_datasets/envs/local/run.sh     # benchmark: 3 repetitions into results/runs/local-bench-<stamp>/
#                                                   # + summary.md (examples_core/bench_summary.py)
# Extra arguments go to every run (e.g. --n 50). prophet-batch is the PyPI release pinned in uv.lock; development:
# PROPHET_BATCH_LOCAL=../prophet-batch runs against that checkout instead (uv run --with-editable).
set -e
cd "$(dirname "$0")/../../.."
DATASETS="${DATASETS:-m5_item_store m4_daily m5_item}"
uv run python -m public_datasets.pipeline.data $DATASETS
if [ -n "$REPS" ]; then
  OUT=public_datasets/results/runs/local-bench-$(date +%Y%m%d-%H%M%S)
  set -- --out "$OUT" "$@"
fi
run() {
  if [ -n "$PROPHET_BATCH_LOCAL" ]; then
    uv run --with-editable "$PROPHET_BATCH_LOCAL" python -m public_datasets.pipeline.run --env local "$@"
  else
    uv run python -m public_datasets.pipeline.run --env local "$@"
  fi
}
rep=1
while [ "$rep" -le "${REPS:-1}" ]; do
  for d in $DATASETS; do run --dataset "$d" "$@"; done
  rep=$((rep + 1))
done
if [ -n "$REPS" ]; then
  uv run python -m examples_core.bench_summary "$OUT" > "$OUT/summary.md"
  echo "summary: $OUT/summary.md"
fi
