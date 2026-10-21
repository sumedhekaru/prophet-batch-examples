#!/bin/sh
# Local Spark standalone cluster from the test image: a master, 2 workers (2 cores each) and a separate driver, so
# executors start in their own containers as on Dataproc. Data and results are folders standing in for the bucket.
#   sh walmart_grocery_forecasting/envs/dataproc/local/cluster.sh --method batch|stock [--n 100] [--run-id ID]
set -e
cd "$(dirname "$0")/../../../.."
IMG=prophet-batch-examples/walmart-spark:local-test
SPARK=/usr/local/lib/python3.12/site-packages/pyspark
mkdir -p data/spark-out && chmod 777 data/spark-out
docker network create pbe-spark >/dev/null 2>&1 || true
cleanup() { docker rm -f pbe-master pbe-worker-1 pbe-worker-2 >/dev/null 2>&1 || true; docker network rm pbe-spark >/dev/null 2>&1 || true; }
trap cleanup EXIT
docker run -d --name pbe-master --network pbe-spark -e SPARK_HOME=$SPARK $IMG \
  $SPARK/bin/spark-class org.apache.spark.deploy.master.Master --host pbe-master >/dev/null
for i in 1 2; do
  docker run -d --name pbe-worker-$i --network pbe-spark --cpus 2 -e SPARK_HOME=$SPARK -e SPARK_WORKER_DIR=/tmp/spark-work \
    -v "$PWD/data/m5:/data:ro" $IMG \
    $SPARK/bin/spark-class org.apache.spark.deploy.worker.Worker spark://pbe-master:7077 --cores 2 --memory 2g >/dev/null
done
sleep 8
docker run --rm --name pbe-driver --network pbe-spark --cpus 2 -e SPARK_HOME=$SPARK \
  -v "$PWD/data/m5:/data:ro" -v "$PWD/data/spark-out:/out" \
  -v "$PWD/walmart_grocery_forecasting/envs/dataproc/spark_main.py:/job/spark_main.py:ro" $IMG \
  $SPARK/bin/spark-submit --master spark://pbe-master:7077 --conf spark.driver.host=pbe-driver \
    --conf spark.executor.instances=2 --conf spark.executor.cores=2 --conf spark.cores.max=4 \
    --conf spark.executor.memory=1500m \
    /job/spark_main.py \
    --data file:///data --out file:///out --wait 120 "$@"
