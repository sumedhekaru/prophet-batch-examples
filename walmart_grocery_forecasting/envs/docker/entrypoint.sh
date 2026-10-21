#!/bin/sh
# Fetch the data if missing (verified by checksum), then run the use case; arguments go to pipeline.run.
set -e
python -m walmart_grocery_forecasting.pipeline.data
exec python -m walmart_grocery_forecasting.pipeline.run --env "${RUN_ENV:-docker}" "$@"
