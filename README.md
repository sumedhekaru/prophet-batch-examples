# prophet-batch-examples

Realistic, runnable use cases for [prophet-batch](https://github.com/sumedhekaru/prophet-batch): fitting and
forecasting many [Prophet](https://github.com/facebook/prophet) models at once. Each use case reports **accuracy and
speed** against stock Prophet on the same data, in the environments people actually run: a laptop, Docker, Cloud Run
jobs, Dataproc and Spark.

Running these is also how prophet-batch gets tested in practice. Bugs found here are reported to the repository they
belong to (prophet-batch, or Prophet itself) and fixed there.

Status: in development. The first use case runs locally, in a local Linux container, as a Cloud Run job and on Spark (Dataproc Serverless).

## Use cases

| Folder | Data | Question |
|---|---|---|
| [walmart_grocery_forecasting](walmart_grocery_forecasting/) | M5 (Walmart), FOODS category, item level: 1,437 daily series | 28-day forecasts: same accuracy as stock Prophet, 7.4–11× faster than a stock process pool on the same cores (macOS, Linux, Cloud Run, Spark, Windows) |

## Layout

```
README.md                          # this file
walmart_grocery_forecasting/
  README.md                        # the use case: data, model, metrics, results
  pipeline/                        # shared code: load data, fit (stock and prophet-batch), forecast, evaluate
  envs/                            # thin per-environment wrappers around pipeline/ (no copied forecasting code)
    local/                         # macOS / Linux / Windows: run script + notebook
    docker/                        # local Linux image
    cloudrun_job/                  # Cloud Run job image (simulated locally with Docker first)
    dataproc/                      # image based on the official Dataproc image (simulated locally first)
  results/                         # result summaries (markdown), on released prophet-batch; raw JSON stays local
    history/                       # pre-release results (prophet-batch from a local checkout)
```

## Setup

Needs [uv](https://docs.astral.sh/uv/). prophet-batch is installed from PyPI, pinned to a release in `pyproject.toml`
and `uv.lock` (what `pip install prophet-batch` gives you), so the results here are reproducible with released code:

```
git clone https://github.com/sumedhekaru/prophet-batch-examples.git
cd prophet-batch-examples
uv sync          # Python 3.12, prophet==1.5.0 and prophet-batch==0.1.1 from PyPI, jupyter
```

Developing prophet-batch itself: with a checkout of it next to this repo, `PROPHET_BATCH_LOCAL=../prophet-batch` runs
the scripts against that checkout instead (`uv run --with-editable` locally, a wheel built from it in the images).
Each run record says which was used: `prophet-batch 0.1.1 (PyPI)` or `prophet-batch 0.1.1 (local <commit>)`.

## Principles

- Data is downloaded by a script and verified by checksum; it is never committed.
- Every result records the machine, environment and package versions, and can be rerun with one command.
- Published results use released prophet-batch from PyPI (the run records say "prophet-batch 0.1.1 (PyPI)");
  results from unreleased code are not published here.
- Stock Prophet and prophet-batch get identical inputs and model settings.
