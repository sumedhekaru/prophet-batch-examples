# prophet-batch-examples

Realistic, runnable use cases for [prophet-batch](https://github.com/sumedhekaru/prophet-batch): fitting and
forecasting many [Prophet](https://github.com/facebook/prophet) models at once. Each use case reports **accuracy and
speed** against stock Prophet on the same data, in the environments people actually run: a laptop, Docker, Cloud Run
jobs, Dataproc and Spark.

Running these is also how prophet-batch gets tested in practice. Bugs found here are reported to the repository they
belong to (prophet-batch, or Prophet itself) and fixed there.

Status: in development, private. The first use case runs locally, in a local Linux container and as a Cloud Run job; Dataproc comes next.

## Use cases

| Folder | Data | Question |
|---|---|---|
| [walmart_grocery_forecasting](walmart_grocery_forecasting/) | M5 (Walmart), FOODS category, item level: 1,437 daily series | 28-day forecasts: same accuracy as stock Prophet, 8.6–10× faster than a 10-process stock pool (local, M4) |

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
  results/                         # result summaries (markdown); raw JSON stays local
```

## Setup

Needs [uv](https://docs.astral.sh/uv/) and, for now, a clone of prophet-batch next to this repo (it moves to PyPI
later):

```
git clone https://github.com/sumedhekaru/prophet-batch.git
git clone https://github.com/sumedhekaru/prophet-batch-examples.git
cd prophet-batch-examples
uv sync          # Python 3.12, prophet==1.5.0 from PyPI, prophet-batch (editable, ../prophet-batch), jupyter
```

## Principles

- Data is downloaded by a script and verified by checksum; it is never committed.
- Every result records the machine, environment and package versions, and can be rerun with one command.
- Stock Prophet and prophet-batch get identical inputs and model settings.
