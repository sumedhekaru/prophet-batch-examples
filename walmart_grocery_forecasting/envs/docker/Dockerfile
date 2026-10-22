# Local Linux image for walmart_grocery_forecasting. Build with build.sh (it prepares build/ first):
#   sh walmart_grocery_forecasting/envs/docker/build.sh
# The build context is the repo root; .dockerignore keeps data and results out.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1

# Runtime dependencies pinned from uv.lock (prophet-batch from PyPI), or, for development, a prophet-batch wheel built
# from a local checkout (build.sh with PROPHET_BATCH_LOCAL).
COPY walmart_grocery_forecasting/envs/docker/build/ /tmp/pkgs/
RUN pip install --no-cache-dir -r /tmp/pkgs/requirements.txt $(ls /tmp/pkgs/*.whl 2>/dev/null) \
    && rm -rf /tmp/pkgs

WORKDIR /app
COPY examples_core/ examples_core/
COPY walmart_grocery_forecasting/__init__.py walmart_grocery_forecasting/
COPY walmart_grocery_forecasting/pipeline/ walmart_grocery_forecasting/pipeline/
COPY walmart_grocery_forecasting/envs/docker/entrypoint.sh /app/entrypoint.sh

ARG EXAMPLES_COMMIT=unknown
ARG PROPHET_BATCH_COMMIT=
ENV EXAMPLES_COMMIT=$EXAMPLES_COMMIT PROPHET_BATCH_COMMIT=$PROPHET_BATCH_COMMIT

# Data and results are volumes: /app/data and /app/walmart_grocery_forecasting/results/runs
ENTRYPOINT ["sh", "/app/entrypoint.sh"]
