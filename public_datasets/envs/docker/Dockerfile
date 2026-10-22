# Linux image for public_datasets. Build with build.sh (it prepares build/ first):
#   sh public_datasets/envs/docker/build.sh
# The build context is the repo root; .dockerignore keeps data and results out.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1

# Runtime dependencies pinned from uv.lock (prophet-batch from PyPI), or, for development, a prophet-batch wheel built
# from a local checkout (build.sh with PROPHET_BATCH_LOCAL).
COPY public_datasets/envs/docker/build/ /tmp/pkgs/
RUN pip install --no-cache-dir -r /tmp/pkgs/requirements.txt $(ls /tmp/pkgs/*.whl 2>/dev/null) \
    && rm -rf /tmp/pkgs

WORKDIR /app
COPY examples_core/ examples_core/
COPY public_datasets/__init__.py public_datasets/
COPY public_datasets/pipeline/ public_datasets/pipeline/
COPY public_datasets/envs/docker/entrypoint.sh /app/entrypoint.sh

ARG EXAMPLES_COMMIT=unknown
ARG PROPHET_BATCH_COMMIT=
ENV EXAMPLES_COMMIT=$EXAMPLES_COMMIT PROPHET_BATCH_COMMIT=$PROPHET_BATCH_COMMIT

# Data and results are volumes: /app/data and /app/public_datasets/results/runs
ENTRYPOINT ["sh", "/app/entrypoint.sh"]
