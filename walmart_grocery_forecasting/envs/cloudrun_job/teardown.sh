#!/bin/sh
# Delete everything deploy.sh created: the job (and its executions), the Artifact Registry repository (all images)
# and the bucket (data and results; deploy.sh already copied the results to results/runs/).
#   PROJECT=my-project REGION=us-east1 BUCKET=my-bucket sh walmart_grocery_forecasting/envs/cloudrun_job/teardown.sh
set -e
: "${PROJECT:?set PROJECT}" "${REGION:?set REGION}" "${BUCKET:?set BUCKET}"
gcloud run jobs delete walmart-forecast --project "$PROJECT" --region "$REGION" --quiet || true
gcloud artifacts repositories delete prophet-batch-examples --project "$PROJECT" --location "$REGION" --quiet || true
gcloud storage rm -r "gs://$BUCKET" || true
