#!/bin/sh
# Run the use case as a Dataproc Serverless batch (PySpark, custom container). Needs gcloud (logged in), Docker, and
#   PROJECT  REGION  BUCKET   (bucket created if missing)
#   EXECUTORS / CORES  executor count and cores each (default 2 × 4; Serverless allows 4, 8 or 16 cores)
#   ITEM_GROUPS (16), STOCK_N (300: items for the stock run, extrapolated)
# Serverless needs Private Google Access on the subnet (default network); turned on here if off, and teardown.sh turns
# it back off (it records the original state in .pga-was-off). Results: gs://$BUCKET/results/ → results/runs/.
set -e
: "${PROJECT:?set PROJECT}" "${REGION:?set REGION}" "${BUCKET:?set BUCKET}"
EXECUTORS="${EXECUTORS:-2}" CORES="${CORES:-4}" ITEM_GROUPS="${ITEM_GROUPS:-16}" STOCK_N="${STOCK_N:-300}"
cd "$(dirname "$0")/../../.."
D=walmart_grocery_forecasting/envs/dataproc
IMAGE="$REGION-docker.pkg.dev/$PROJECT/prophet-batch-examples/walmart-spark:$(git rev-parse --short HEAD)"
# Runtime 3.0 runs workloads with end-user credentials by default (needs an extra OAuth consent); run as the
# project's default compute service account instead (SA overrides it).
SA="${SA:-$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')-compute@developer.gserviceaccount.com}"

# 0. Network: Private Google Access on the default subnet
if [ "$(gcloud compute networks subnets describe default --project "$PROJECT" --region "$REGION" \
        --format='value(privateIpGoogleAccess)')" != "True" ]; then
  gcloud compute networks subnets update default --project "$PROJECT" --region "$REGION" \
    --enable-private-ip-google-access
  touch "$D/.pga-was-off"
fi

# 1. Image
gcloud artifacts repositories describe prophet-batch-examples --project "$PROJECT" --location "$REGION" >/dev/null 2>&1 \
  || gcloud artifacts repositories create prophet-batch-examples --project "$PROJECT" --location "$REGION" \
       --repository-format docker
gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet
TAG="$IMAGE" sh "$D/build.sh"
docker push -q "$IMAGE"

# 2. Data: the two CSVs the job reads (extracted from the verified archive)
gcloud storage buckets describe "gs://$BUCKET" --project "$PROJECT" >/dev/null 2>&1 \
  || gcloud storage buckets create "gs://$BUCKET" --project "$PROJECT" --location "$REGION" \
       --uniform-bucket-level-access
gcloud storage cp -n data/m5/sales_train_evaluation.csv data/m5/calendar.csv "gs://$BUCKET/data/m5/"

# 3. Batch: fixed size (no autoscaling); waits and streams the driver output
gcloud dataproc batches submit pyspark "$D/spark_main.py" --project "$PROJECT" --region "$REGION" \
  --batch "walmart-$(date +%Y%m%d-%H%M%S)" --version 3.0 --container-image "$IMAGE" --subnet default \
  --deps-bucket "gs://$BUCKET" --user-workload-authentication-type SERVICE_ACCOUNT --service-account "$SA" \
  --properties "spark.dynamicAllocation.enabled=false,spark.executor.instances=$EXECUTORS,spark.executor.cores=$CORES,spark.driver.cores=4" \
  -- --data "gs://$BUCKET/data/m5" --out "gs://$BUCKET/results" --groups "$ITEM_GROUPS" --stock-n "$STOCK_N"
mkdir -p walmart_grocery_forecasting/results/runs
gcloud storage cp "gs://$BUCKET/results/*" walmart_grocery_forecasting/results/runs/
