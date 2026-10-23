#!/bin/sh
# Deploy and run the use case as a Cloud Run job. Needs gcloud (logged in), Docker, and:
#   PROJECT  GCP project id      REGION  e.g. us-east1      BUCKET  bucket name (created if missing)
#   MODELS   variants to run, in order (default: "default events events_snap")
#   CPU / MEMORY  job size (default 4 vCPU / 8Gi: enough for 1,437 items; the pool uses one worker per vCPU)
#   JOB_ARGS extra arguments for pipeline.run, comma-separated as gcloud wants them (e.g. "--n,300")
#   REPS     benchmark: REPS repetitions (each execution on a fresh instance) into results/runs/cloudrun-bench-<stamp>/
#            + summary.md (examples_core/bench_summary.py)
#   PROJECT=my-project REGION=us-east1 BUCKET=my-bucket sh walmart_grocery_forecasting/envs/cloudrun_job/deploy.sh
# Results: gs://$BUCKET/results/ (copied to results/runs/ at the end). Remove everything with teardown.sh.
set -e
: "${PROJECT:?set PROJECT}" "${REGION:?set REGION}" "${BUCKET:?set BUCKET}"
MODELS="${MODELS:-default events events_snap}"
CPU="${CPU:-4}" MEMORY="${MEMORY:-8Gi}"
cd "$(dirname "$0")/../../.."
REPO="$REGION-docker.pkg.dev/$PROJECT/prophet-batch-examples"
IMAGE="$REPO/walmart:$(git rev-parse --short HEAD)"

# 1. Image: build for amd64, push to Artifact Registry
gcloud artifacts repositories describe prophet-batch-examples --project "$PROJECT" --location "$REGION" >/dev/null 2>&1 \
  || gcloud artifacts repositories create prophet-batch-examples --project "$PROJECT" --location "$REGION" \
       --repository-format docker
gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet
TAG="$IMAGE" sh walmart_grocery_forecasting/envs/cloudrun_job/build.sh -q
docker push -q "$IMAGE"

# 2. Data: the verified M5 archive in the bucket (the job extracts what it needs on first run)
gcloud storage buckets describe "gs://$BUCKET" --project "$PROJECT" >/dev/null 2>&1 \
  || gcloud storage buckets create "gs://$BUCKET" --project "$PROJECT" --location "$REGION" \
       --uniform-bucket-level-access
gcloud storage cp -n data/m5/m5.zip "gs://$BUCKET/data/m5/m5.zip"

# 3. Job: one task; the bucket is a volume at /mnt/gcs
gcloud run jobs deploy walmart-forecast --project "$PROJECT" --region "$REGION" --image "$IMAGE" \
  --cpu "$CPU" --memory "$MEMORY" --tasks 1 --max-retries 0 --task-timeout 3600 \
  --add-volume name=gcs,type=cloud-storage,bucket="$BUCKET" --add-volume-mount volume=gcs,mount-path=/mnt/gcs \
  --set-env-vars DATA_DIR=/mnt/gcs/data/m5,OUT_DIR=/mnt/gcs/results,RUN_ENV=cloudrun

# 4. One execution per model variant (REPS times), then the results back to results/runs/
SUB= ARGS=
if [ -n "$REPS" ]; then SUB=cloudrun-bench-$(date +%Y%m%d-%H%M%S) ARGS=",--out,/mnt/gcs/results/$SUB"; fi
rep=1
while [ "$rep" -le "${REPS:-1}" ]; do
  for model in $MODELS; do
    echo "== $model (repetition $rep)"
    gcloud run jobs execute walmart-forecast --project "$PROJECT" --region "$REGION" --args=--model,"$model$ARGS${JOB_ARGS:+,$JOB_ARGS}" --wait \
      || echo "execution FAILED: $model (repetition $rep)"
  done
  rep=$((rep + 1))
done
mkdir -p walmart_grocery_forecasting/results/runs
if [ -n "$REPS" ]; then
  OUT=walmart_grocery_forecasting/results/runs/$SUB
  mkdir -p "$OUT"
  # sliced (parallel) downloads hung for 30 min in K4: one stream per file, and retry
  for try in 1 2 3; do
    CLOUDSDK_STORAGE_SLICED_OBJECT_DOWNLOAD_THRESHOLD=0 gcloud storage rsync "gs://$BUCKET/results/$SUB" "$OUT" && break
    sleep 10
  done
  uv run python -m examples_core.bench_summary "$OUT" > "$OUT/summary.md"
  echo "summary: $OUT/summary.md"
else
  gcloud storage cp "gs://$BUCKET/results/*" walmart_grocery_forecasting/results/runs/
fi
