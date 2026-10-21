#!/bin/sh
# Fetch the data if missing (verified by checksum), then run the use case; arguments go to pipeline.run.
# DATA_DIR / OUT_DIR override the default paths (e.g. a mounted Cloud Storage bucket in a Cloud Run job).
set -e
DATA_DIR="${DATA_DIR:-/app/data/m5}"
OUT_DIR="${OUT_DIR:-/app/walmart_grocery_forecasting/results/runs}"
python -m walmart_grocery_forecasting.pipeline.data --data-dir "$DATA_DIR"
exec python -m walmart_grocery_forecasting.pipeline.run --env "${RUN_ENV:-docker}" --data-dir "$DATA_DIR" \
  --out "$OUT_DIR" "$@"
