#!/bin/sh
# Delete what deploy.sh created: batches, the Artifact Registry repository, the bucket, any Dataproc staging/temp
# buckets created during the run (KEEP lists bucket names that existed before and must stay), and restore Private
# Google Access if deploy.sh turned it on.
set -e
: "${PROJECT:?set PROJECT}" "${REGION:?set REGION}" "${BUCKET:?set BUCKET}"
cd "$(dirname "$0")/../../.."
D=walmart_grocery_forecasting/envs/dataproc
for b in $(gcloud dataproc batches list --project "$PROJECT" --region "$REGION" --format='value(name.basename())' \
             | grep '^walmart-'); do
  gcloud dataproc batches delete "$b" --project "$PROJECT" --region "$REGION" --quiet || true
done
gcloud artifacts repositories delete prophet-batch-examples --project "$PROJECT" --location "$REGION" --quiet || true
gcloud storage rm -r "gs://$BUCKET" || true
for b in $(gcloud storage buckets list --project "$PROJECT" --format='value(name)'); do
  case " $KEEP " in *" $b "*) ;; *) case "$b" in dataproc-staging-*|dataproc-temp-*) gcloud storage rm -r "gs://$b" || true;; esac;; esac
done
if [ -f "$D/.pga-was-off" ]; then
  gcloud compute networks subnets update default --project "$PROJECT" --region "$REGION" \
    --no-enable-private-ip-google-access
  rm "$D/.pga-was-off"
fi
