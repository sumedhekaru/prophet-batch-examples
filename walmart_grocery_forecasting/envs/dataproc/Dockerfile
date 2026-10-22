# Custom container for Dataproc Serverless (Spark runtime 3.0). Per Google's requirements: Debian 12, procps + tini,
# user spark (uid/gid 1099), no Spark or Java in the image (Dataproc mounts both), PYSPARK_PYTHON -> our Python.
# Build with build.sh (it prepares build/ first). The build context is the repo root.
FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update && apt-get install -y --no-install-recommends procps tini \
    && rm -rf /var/lib/apt/lists/*

COPY walmart_grocery_forecasting/envs/dataproc/requirements.txt walmart_grocery_forecasting/envs/dataproc/build/ /tmp/pkgs/
RUN pip install --no-cache-dir -r /tmp/pkgs/requirements.txt -r /tmp/pkgs/prophet-batch.txt \
    $(ls /tmp/pkgs/*.whl 2>/dev/null) && rm -rf /tmp/pkgs

# The pipeline as an installed package, so Spark's Python workers import it without any PYTHONPATH setup.
ARG SITE=/usr/local/lib/python3.12/site-packages
COPY walmart_grocery_forecasting/__init__.py $SITE/walmart_grocery_forecasting/
COPY walmart_grocery_forecasting/pipeline/ $SITE/walmart_grocery_forecasting/pipeline/

ARG EXAMPLES_COMMIT=unknown
ARG PROPHET_BATCH_COMMIT=
ENV EXAMPLES_COMMIT=$EXAMPLES_COMMIT PROPHET_BATCH_COMMIT=$PROPHET_BATCH_COMMIT PYSPARK_PYTHON=/usr/local/bin/python3
# One BLAS thread per Python worker: each executor runs one worker per core.
ENV OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1

RUN groupadd -g 1099 spark && useradd -u 1099 -g 1099 -d /home/spark -m spark
USER spark
