#!/bin/sh
# Deploy and run the public datasets as a Cloud Run job. Needs gcloud (logged in), Docker, and:
#   PROJECT  GCP project id      REGION  e.g. us-east1      BUCKET  bucket name (created if missing)
#   DATASETS datasets to run (default: the three large ones: m5_item_store m4_daily m5_item)
#   CPU / MEMORY  job size (default 8 vCPU / 32Gi: item × store needs ≈ 9 GB; the pool uses one worker per vCPU)
#   JOB_ARGS extra arguments for pipeline.run, comma-separated as gcloud wants them (e.g. "--n,300")
#   REPS     benchmark: REPS repetitions into results/runs/cloudrun-bench-<stamp>/ + summary.md
#   SIDE_BY_SIDE=1  run the datasets at the same time (each execution is its own instance; one dataset's
#            repetitions stay in order). Default 0: one execution at a time.
#   PROJECT=my-project REGION=us-east1 BUCKET=my-bucket sh public_datasets/envs/cloudrun_job/deploy.sh
# Results: gs://$BUCKET/results/ (copied to results/runs/ at the end). Remove everything with teardown.sh.
set -e
: "${PROJECT:?set PROJECT}" "${REGION:?set REGION}" "${BUCKET:?set BUCKET}"
DATASETS="${DATASETS:-m5_item_store m4_daily m5_item}"
CPU="${CPU:-8}" MEMORY="${MEMORY:-32Gi}"
cd "$(dirname "$0")/../../.."
REPO="$REGION-docker.pkg.dev/$PROJECT/prophet-batch-examples"
IMAGE="$REPO/public-datasets:$(git rev-parse --short HEAD)"

# 1. Image: build for amd64, push to Artifact Registry
gcloud artifacts repositories describe prophet-batch-examples --project "$PROJECT" --location "$REGION" >/dev/null 2>&1 \
  || gcloud artifacts repositories create prophet-batch-examples --project "$PROJECT" --location "$REGION" \
       --repository-format docker
gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet
TAG="$IMAGE" sh public_datasets/envs/cloudrun_job/build.sh -q
docker push -q "$IMAGE"

# 2. Data: the verified downloads, already extracted, so the job only reads the bucket (the entrypoint verifies the
#    checksums and finds nothing to extract)
gcloud storage buckets describe "gs://$BUCKET" --project "$PROJECT" >/dev/null 2>&1 \
  || gcloud storage buckets create "gs://$BUCKET" --project "$PROJECT" --location "$REGION" \
       --uniform-bucket-level-access
uv run python -m public_datasets.pipeline.data $DATASETS
for src in m5 m4 tourism; do
  [ -d "data/$src" ] && gcloud storage cp -n -r "data/$src" "gs://$BUCKET/data/"
done

# 3. Job: one task; the bucket is a volume at /mnt/gcs
gcloud run jobs deploy public-datasets-forecast --project "$PROJECT" --region "$REGION" --image "$IMAGE" \
  --cpu "$CPU" --memory "$MEMORY" --tasks 1 --max-retries 0 --task-timeout 14400 \
  --add-volume name=gcs,type=cloud-storage,bucket="$BUCKET" --add-volume-mount volume=gcs,mount-path=/mnt/gcs \
  --set-env-vars DATA_DIR=/mnt/gcs/data,OUT_DIR=/mnt/gcs/results,RUN_ENV=cloudrun

# 4. One execution per dataset (REPS times), then the results back to results/runs/
SUB= ARGS=
if [ -n "$REPS" ]; then SUB=cloudrun-bench-$(date +%Y%m%d-%H%M%S) ARGS=",--out,/mnt/gcs/results/$SUB"; fi
chain() {  # one dataset, its repetitions in order
  rep=1
  while [ "$rep" -le "${REPS:-1}" ]; do
    echo "== $1 (repetition $rep)"
    gcloud run jobs execute public-datasets-forecast --project "$PROJECT" --region "$REGION" \
      --args=--dataset,"$1$ARGS${JOB_ARGS:+,$JOB_ARGS}" --wait || echo "execution FAILED: $1 (repetition $rep)"
    rep=$((rep + 1))
  done
}
if [ "${SIDE_BY_SIDE:-0}" = 1 ]; then
  for d in $DATASETS; do chain "$d" & done
  wait
else
  for d in $DATASETS; do chain "$d"; done
fi
mkdir -p public_datasets/results/runs
if [ -n "$REPS" ]; then
  OUT=public_datasets/results/runs/$SUB
  mkdir -p "$OUT"
  gcloud storage cp "gs://$BUCKET/results/$SUB/*" "$OUT/"
  uv run python -m examples_core.bench_summary "$OUT" > "$OUT/summary.md"
  echo "summary: $OUT/summary.md"
else
  gcloud storage cp "gs://$BUCKET/results/*" public_datasets/results/runs/
fi
