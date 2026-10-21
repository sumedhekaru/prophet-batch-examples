# Local Linux image for walmart_grocery_forecasting. Build with build.sh (it prepares build/ first):
#   sh walmart_grocery_forecasting/envs/docker/build.sh
# The build context is the repo root; .dockerignore keeps data and results out.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1

# Runtime dependencies pinned from uv.lock, then the prophet-batch wheel built from the sibling clone.
COPY walmart_grocery_forecasting/envs/docker/build/ /tmp/pkgs/
RUN pip install --no-cache-dir -r /tmp/pkgs/requirements.txt /tmp/pkgs/*.whl \
    && rm -rf /tmp/pkgs

WORKDIR /app
COPY walmart_grocery_forecasting/__init__.py walmart_grocery_forecasting/
COPY walmart_grocery_forecasting/pipeline/ walmart_grocery_forecasting/pipeline/
COPY walmart_grocery_forecasting/envs/docker/entrypoint.sh /app/entrypoint.sh

ARG EXAMPLES_COMMIT=unknown
ARG PROPHET_BATCH_COMMIT=unknown
ENV EXAMPLES_COMMIT=$EXAMPLES_COMMIT PROPHET_BATCH_COMMIT=$PROPHET_BATCH_COMMIT

# Data and results are volumes: /app/data and /app/walmart_grocery_forecasting/results/runs
ENTRYPOINT ["sh", "/app/entrypoint.sh"]
