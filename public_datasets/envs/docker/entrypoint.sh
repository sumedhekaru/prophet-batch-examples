#!/bin/sh
# Fetch the dataset if missing (verified by checksum), then run it; arguments go to pipeline.run (incl. --dataset).
# DATA_DIR / OUT_DIR override the default paths (e.g. a mounted Cloud Storage bucket in a Cloud Run job).
set -e
DATA_DIR="${DATA_DIR:-/app/data}"
OUT_DIR="${OUT_DIR:-/app/public_datasets/results/runs}"
dataset=$(echo "$@" | sed -n 's/.*--dataset[ =]\([a-z0-9_]*\).*/\1/p')
python -m public_datasets.pipeline.data --data-dir "$DATA_DIR" $dataset
exec python -m public_datasets.pipeline.run --env "${RUN_ENV:-docker}" --data-dir "$DATA_DIR" --out "$OUT_DIR" "$@"
