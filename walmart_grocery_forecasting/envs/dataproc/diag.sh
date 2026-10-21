#!/bin/sh
# Run diag.py as two Dataproc batches (our container, Dataproc's default container) and print their DIAG records.
#   PROJECT=... REGION=... BUCKET=... sh walmart_grocery_forecasting/envs/dataproc/diag.sh
# Creates the image repository / bucket / Private Google Access if missing (teardown.sh removes them).
set -e
: "${PROJECT:?set PROJECT}" "${REGION:?set REGION}" "${BUCKET:?set BUCKET}"
cd "$(dirname "$0")/../../.."
D=walmart_grocery_forecasting/envs/dataproc
IMAGE="$REGION-docker.pkg.dev/$PROJECT/prophet-batch-examples/walmart-spark:$(git rev-parse --short HEAD)"
SA="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')-compute@developer.gserviceaccount.com"
PROPS="spark.dynamicAllocation.enabled=false,spark.executor.instances=2,spark.executor.cores=4,spark.driver.cores=4"
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
TAG="$IMAGE" sh "$D/build.sh" && docker push -q "$IMAGE"
for variant in custom default; do
  id="diag-$variant-$(date +%H%M%S)"
  extra=""; [ "$variant" = custom ] && extra="--container-image $IMAGE"
  gcloud dataproc batches submit pyspark "$D/diag.py" --project "$PROJECT" --region "$REGION" --batch "$id" \
    --version 3.0 $extra --subnet default --deps-bucket "gs://$BUCKET" \
    --user-workload-authentication-type SERVICE_ACCOUNT --service-account "$SA" --properties "$PROPS" >/dev/null 2>&1 \
    || echo "batch $id: submit/run failed"
  echo "== $variant ($id): $(gcloud dataproc batches describe "$id" --project "$PROJECT" --region "$REGION" --format='value(state)')"
  for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
    line=$(gcloud logging read "resource.type=\"cloud_dataproc_batch\" AND resource.labels.batch_id=\"$id\" AND textPayload:\"DIAG \"" \
             --project "$PROJECT" --freshness=1h --format='value(textPayload)' 2>/dev/null)
    [ -n "$line" ] && break; sleep 10
  done
  echo "$line"
done
