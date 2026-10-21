#!/bin/sh
# Deploy and run the use case as a Cloud Run job (not yet run on GCP). Needs gcloud, Docker, and:
#   PROJECT  GCP project id          REGION  e.g. us-central1          BUCKET  bucket name (created if missing)
#   MODEL    default | events | events_snap (default: default)
#   PROJECT=my-project REGION=us-central1 BUCKET=my-bucket sh walmart_grocery_forecasting/envs/cloudrun_job/deploy.sh
set -e
: "${PROJECT:?set PROJECT}" "${REGION:?set REGION}" "${BUCKET:?set BUCKET}"
MODEL="${MODEL:-default}"
cd "$(dirname "$0")/../../.."
REPO="$REGION-docker.pkg.dev/$PROJECT/prophet-batch-examples"
IMAGE="$REPO/walmart:$(git rev-parse --short HEAD)"

# 1. Image: build for amd64, push to Artifact Registry
gcloud artifacts repositories describe prophet-batch-examples --project "$PROJECT" --location "$REGION" >/dev/null 2>&1 \
  || gcloud artifacts repositories create prophet-batch-examples --project "$PROJECT" --location "$REGION" \
       --repository-format docker
gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet
TAG="$IMAGE" sh walmart_grocery_forecasting/envs/cloudrun_job/build.sh
docker push "$IMAGE"

# 2. Data: the verified M5 archive in the bucket (the job extracts what it needs on first run)
gcloud storage buckets describe "gs://$BUCKET" --project "$PROJECT" >/dev/null 2>&1 \
  || gcloud storage buckets create "gs://$BUCKET" --project "$PROJECT" --location "$REGION"
gcloud storage cp -n data/m5/m5.zip "gs://$BUCKET/data/m5/m5.zip"

# 3. Job: 8 vCPU / 32 GiB, one task; the bucket is a volume at /mnt/gcs
gcloud run jobs deploy walmart-forecast --project "$PROJECT" --region "$REGION" --image "$IMAGE" \
  --cpu 8 --memory 32Gi --tasks 1 --max-retries 0 --task-timeout 3600 \
  --add-volume name=gcs,type=cloud-storage,bucket="$BUCKET" --add-volume-mount volume=gcs,mount-path=/mnt/gcs \
  --set-env-vars DATA_DIR=/mnt/gcs/data/m5,OUT_DIR=/mnt/gcs/results,RUN_ENV=cloudrun \
  --args=--model,"$MODEL"
gcloud run jobs execute walmart-forecast --project "$PROJECT" --region "$REGION" --wait
echo "results: gs://$BUCKET/results/"
