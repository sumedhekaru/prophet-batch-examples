#!/bin/sh
# Reproducible Spark benchmark of the public datasets on Dataproc Serverless (protocol of track F5, as
# walmart_grocery_forecasting/envs/dataproc/benchmark.sh): per dataset, stock vs prophet-batch, one method per batch,
# REPS repetitions in alternating order, every phase timed, then teardown.
#   PROJECT=... REGION=... BUCKET=... sh public_datasets/envs/dataproc/benchmark.sh
# Options: DATASETS ("m5_item_store m4_daily m5_item"), REPS (3), METHODS ("batch stock"), JOB_ARGS (extra job
# arguments, e.g. "--warmup --groups 32"), EXECUTORS (2), CORES per executor (4), DRIVER_CORES (4), RUNTIME (2.3),
# TEARDOWN (1). Output: results/runs/dataproc-bench-<stamp>/<dataset>/ with every run's records, the batch resources
# (state history) and summary.md (examples_core/spark_summary.py).
set -e
: "${PROJECT:?set PROJECT}" "${REGION:?set REGION}" "${BUCKET:?set BUCKET}"
DATASETS="${DATASETS:-m5_item_store m4_daily m5_item}"
REPS="${REPS:-3}" EXECUTORS="${EXECUTORS:-2}" CORES="${CORES:-4}" DRIVER_CORES="${DRIVER_CORES:-4}"
RUNTIME="${RUNTIME:-2.3}" TEARDOWN="${TEARDOWN:-1}" METHODS="${METHODS:-batch stock}"
cd "$(dirname "$0")/../../.."
D=public_datasets/envs/dataproc
STAMP=$(date -u +%Y%m%d-%H%M%S)
OUT=public_datasets/results/runs/dataproc-bench-$STAMP
mkdir -p "$OUT"
IMAGE="$REGION-docker.pkg.dev/$PROJECT/prophet-batch-examples/public-spark:$(git rev-parse --short HEAD)"
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
if [ -z "$SKIP_BUILD" ]; then
  TAG="$IMAGE" sh "$D/build.sh"
  docker push -q "$IMAGE" >/dev/null
fi
docker inspect --format '{{index .RepoDigests 0}}' "$IMAGE" > "$OUT/image-digest.txt"
uv run python -m public_datasets.pipeline.data $DATASETS >/dev/null
for src in m5 m4 tourism; do
  [ -d "data/$src" ] && gcloud storage cp -n -r "data/$src" "gs://$BUCKET/data/" >/dev/null 2>&1
done
if [ -n "$PROPHET_BATCH_LOCAL" ]; then PB="local $(git -C "$PROPHET_BATCH_LOCAL" rev-parse --short HEAD)"
else PB=$(uv export --no-default-groups --no-hashes --format requirements.txt 2>/dev/null | grep '^prophet-batch=='); fi
cat > "$OUT/config.json" <<JSON
{"project": "$PROJECT", "region": "$REGION", "runtime": "$RUNTIME", "reps": $REPS, "executors": $EXECUTORS,
 "executor_cores": $CORES, "driver_cores": $DRIVER_CORES, "properties": "$PROPS", "image": "$IMAGE",
 "datasets": "$DATASETS", "job_args": "$JOB_ARGS",
 "examples_commit": "$(git rev-parse --short HEAD)", "prophet_batch": "$PB"}
JSON

# Runs: per dataset, one method per batch, alternating order between repetitions
for dataset in $DATASETS; do
  mkdir -p "$OUT/$dataset"
  rep=1
  while [ "$rep" -le "$REPS" ]; do
    if [ $((rep % 2)) -eq 1 ]; then order="$METHODS"; else order=$(echo $METHODS | awk '{for (i = NF; i > 0; i--) printf "%s ", $i}'); fi
    for method in $order; do
      id=$(echo "bench-$STAMP-$dataset-r$rep-$method" | tr 'A-Z_' 'a-z-')
      log "run $id"
      gcloud dataproc batches submit pyspark "$D/spark_main.py" --project "$PROJECT" --region "$REGION" --batch "$id" \
        --version "$RUNTIME" --container-image "$IMAGE" --subnet default --deps-bucket "gs://$BUCKET" \
        --user-workload-authentication-type SERVICE_ACCOUNT --service-account "$SA" --properties "$PROPS" \
        -- --data "gs://$BUCKET/data" --out "gs://$BUCKET/bench/$STAMP/$dataset" --dataset "$dataset" \
           --method "$method" --run-id "$id" $JOB_ARGS \
        >> "$OUT/submit.log" 2>&1 || log "run $id FAILED (see submit.log)"
      gcloud dataproc batches describe "$id" --project "$PROJECT" --region "$REGION" --format=json > "$OUT/$dataset/$id.batch.json"
      log "$id: $(python3 -c "import json; d=json.load(open('$OUT/$dataset/$id.batch.json')); print(d['state'])")"
    done
    rep=$((rep + 1))
  done
  copied=0
  for try in 1 2 3; do  # one large download failed once without retry (K4: sliced downloads hung; off here); errors go to copy.log
    CLOUDSDK_STORAGE_SLICED_OBJECT_DOWNLOAD_THRESHOLD=0 gcloud storage cp "gs://$BUCKET/bench/$STAMP/$dataset/*" "$OUT/$dataset/" >> "$OUT/copy.log" 2>&1 && { copied=1; break; }
    sleep 10
  done
  [ "$copied" = 1 ] || log "copying $dataset results FAILED (see copy.log)"
  uv run python -m examples_core.spark_summary "$OUT/$dataset" > "$OUT/$dataset/summary.md" \
    && log "summary: $OUT/$dataset/summary.md" || log "summary FAILED for $dataset (raw results are in $OUT/$dataset)"
done

if [ "$TEARDOWN" = 1 ]; then
  log "teardown"
  KEEP="" sh "$D/teardown.sh"
fi
