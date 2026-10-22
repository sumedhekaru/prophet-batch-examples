#!/bin/sh
# Run the public datasets in the image (build it first with build.sh); default: the three large ones. Uses the repo's
# data/ (downloaded into it if missing) and writes public_datasets/results/runs/docker-*. Extra arguments go to
# pipeline.run, e.g. --n 50. DATASETS="..." picks datasets; REPS=3: benchmark, 3 repetitions into
# results/runs/docker-bench-<stamp>/ + summary.md (examples_core/bench_summary.py).
set -e
cd "$(dirname "$0")/../../.."
DATASETS="${DATASETS:-m5_item_store m4_daily m5_item}"
mkdir -p data public_datasets/results/runs
SUB=
if [ -n "$REPS" ]; then
  SUB=docker-bench-$(date +%Y%m%d-%H%M%S)
  set -- --out "/app/public_datasets/results/runs/$SUB" "$@"
fi
rep=1
while [ "$rep" -le "${REPS:-1}" ]; do
  for d in $DATASETS; do
    docker run --rm \
      -v "$PWD/data:/app/data" \
      -v "$PWD/public_datasets/results/runs:/app/public_datasets/results/runs" \
      "${TAG:-prophet-batch-examples/public-datasets:local}" --dataset "$d" "$@"
  done
  rep=$((rep + 1))
done
if [ -n "$REPS" ]; then
  OUT=public_datasets/results/runs/$SUB
  uv run python -m examples_core.bench_summary "$OUT" > "$OUT/summary.md"
  echo "summary: $OUT/summary.md"
fi
