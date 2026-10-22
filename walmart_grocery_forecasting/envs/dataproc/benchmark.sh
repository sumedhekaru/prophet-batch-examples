#!/bin/sh
# Reproducible Spark benchmark on Dataproc Serverless (track F5): stock vs prophet-batch, one method per batch,
# REPS repetitions in alternating order, every phase timed (see pipeline/spark_summary.py), then teardown.
#   PROJECT=... REGION=... BUCKET=... sh walmart_grocery_forecasting/envs/dataproc/benchmark.sh
# Options: REPS (3), METHODS ("batch stock"), JOB_ARGS (extra job arguments, e.g. "--warmup"), EXECUTORS (2), CORES per executor (4), DRIVER_CORES (4), RUNTIME (2.3: runtime 3.0 runs
# PySpark batches in local mode, see results), TEARDOWN (1). Output: results/runs/dataproc-bench-<stamp>/ with every
# run's records, the batch resources (state history, DCU usage) and summary.md. prophet-batch: the PyPI release pinned
# in uv.lock; PROPHET_BATCH_LOCAL=../prophet-batch builds the image from that checkout instead (see build.sh).
set -e
: "${PROJECT:?set PROJECT}" "${REGION:?set REGION}" "${BUCKET:?set BUCKET}"
REPS="${REPS:-3}" EXECUTORS="${EXECUTORS:-2}" CORES="${CORES:-4}" DRIVER_CORES="${DRIVER_CORES:-4}"
RUNTIME="${RUNTIME:-2.3}" TEARDOWN="${TEARDOWN:-1}" METHODS="${METHODS:-batch stock}"
cd "$(dirname "$0")/../../.."
D=walmart_grocery_forecasting/envs/dataproc
STAMP=$(date -u +%Y%m%d-%H%M%S)
OUT=walmart_grocery_forecasting/results/runs/dataproc-bench-$STAMP
mkdir -p "$OUT"
IMAGE="$REGION-docker.pkg.dev/$PROJECT/prophet-batch-examples/walmart-spark:$(git rev-parse --short HEAD)"
SA="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')-compute@developer.gserviceaccount.com"
PROPS="spark.dynamicAllocation.enabled=false,spark.executor.instances=$EXECUTORS,spark.executor.cores=$CORES"
PROPS="$PROPS,spark.driver.cores=$DRIVER_CORES"
log() { echo "$(date -u +%H:%M:%S) $*" | tee -a "$OUT/benchmark.log"; }

# Setup (not part of any run's measurement)
log "setup: network, repository, bucket, image, data"
if [ "$(gcloud compute networks subnets describe default --project "$PROJECT" --region "$REGION" \
        --format='value(privateIpGoogleAccess)')" != "True" ]; then
  gcloud compute networks subnets update default --project "$PROJECT" --region "$REGION" --enable-private-ip-google-access
  touch "$D/.pga-was-off"
fi
gcloud artifacts repositories describe prophet-batch-examples --project "$PROJECT" --location "$REGION" >/dev/null 2>&1 \
  || gcloud artifacts repositories create prophet-batch-examples --project "$PROJECT" --location "$REGION" --repository-format docker
gcloud storage buckets describe "gs://$BUCKET" --project "$PROJECT" >/dev/null 2>&1 \
  || gcloud storage buckets create "gs://$BUCKET" --project "$PROJECT" --location "$REGION" --uniform-bucket-level-access
gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet >/dev/null 2>&1
TAG="$IMAGE" sh "$D/build.sh"
docker push -q "$IMAGE" >/dev/null
docker inspect --format '{{index .RepoDigests 0}}' "$IMAGE" > "$OUT/image-digest.txt"
gcloud storage cp -n data/m5/sales_train_evaluation.csv data/m5/calendar.csv "gs://$BUCKET/data/m5/" >/dev/null 2>&1
if [ -n "$PROPHET_BATCH_LOCAL" ]; then PB="local $(git -C "$PROPHET_BATCH_LOCAL" rev-parse --short HEAD)"
else PB=$(uv export --no-default-groups --no-hashes --format requirements.txt 2>/dev/null | grep '^prophet-batch=='); fi
cat > "$OUT/config.json" <<JSON
{"project": "$PROJECT", "region": "$REGION", "runtime": "$RUNTIME", "reps": $REPS, "executors": $EXECUTORS,
 "executor_cores": $CORES, "driver_cores": $DRIVER_CORES, "properties": "$PROPS", "image": "$IMAGE",
 "examples_commit": "$(git rev-parse --short HEAD)", "prophet_batch": "$PB"}
JSON

# Runs: one method per batch, alternating order
rep=1
while [ "$rep" -le "$REPS" ]; do
  # alternate the order between repetitions
  if [ $((rep % 2)) -eq 1 ]; then order="$METHODS"; else order=$(echo $METHODS | awk '{for (i = NF; i > 0; i--) printf "%s ", $i}'); fi
  for method in $order; do
    id="bench-$STAMP-r$rep-$method"
    id=$(echo "$id" | tr 'A-Z' 'a-z')
    log "run $id"
    gcloud dataproc batches submit pyspark "$D/spark_main.py" --project "$PROJECT" --region "$REGION" --batch "$id" \
      --version "$RUNTIME" --container-image "$IMAGE" --subnet default --deps-bucket "gs://$BUCKET" \
      --user-workload-authentication-type SERVICE_ACCOUNT --service-account "$SA" --properties "$PROPS" \
      -- --data "gs://$BUCKET/data/m5" --out "gs://$BUCKET/bench/$STAMP" --method "$method" --run-id "$id" $JOB_ARGS \
      >> "$OUT/submit.log" 2>&1 || log "run $id FAILED (see submit.log)"
    gcloud dataproc batches describe "$id" --project "$PROJECT" --region "$REGION" --format=json > "$OUT/$id.batch.json"
    log "$id: $(python3 -c "import json; d=json.load(open('$OUT/$id.batch.json')); print(d['state'])")"
  done
  rep=$((rep + 1))
done

# Results
copied=0
for try in 1 2 3; do  # a large download failed once without retry (K4); errors go to copy.log
  gcloud storage cp "gs://$BUCKET/bench/$STAMP/*" "$OUT/" >> "$OUT/copy.log" 2>&1 && { copied=1; break; }
  sleep 10
done
[ "$copied" = 1 ] || log "copying results FAILED (see copy.log)"
uv run python -m walmart_grocery_forecasting.pipeline.spark_summary "$OUT" > "$OUT/summary.md" \
  && log "summary: $OUT/summary.md" || log "summary FAILED (raw results are in $OUT; rerun spark_summary)"
if [ "$TEARDOWN" = 1 ]; then
  log "teardown"
  KEEP="" sh "$D/teardown.sh"
fi
