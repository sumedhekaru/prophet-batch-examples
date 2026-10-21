# prophet-batch-examples

Realistic, runnable use cases for [prophet-batch](https://github.com/sumedhekaru/prophet-batch): fitting and
forecasting many [Prophet](https://github.com/facebook/prophet) models at once. Each use case reports **accuracy and
speed** against stock Prophet on the same data, in the environments people actually run: a laptop, Docker, Cloud Run
jobs, Dataproc and Spark.

Running these is also how prophet-batch gets tested in practice. Bugs found here are reported to the repository they
belong to (prophet-batch, or Prophet itself) and fixed there.

Status: in development, private. Nothing here runs yet; the layout below is the plan.

## Use cases

| Folder | Data | Question |
|---|---|---|
| [walmart_grocery_forecasting](walmart_grocery_forecasting/) | M5 (Walmart), FOODS category, item level: 1,437 daily series | 28-day forecasts: same accuracy as stock Prophet, how much faster? |

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

## Principles

- Data is downloaded by a script and verified by checksum; it is never committed.
- Every result records the machine, environment and package versions, and can be rerun with one command.
- Stock Prophet and prophet-batch get identical inputs and model settings.
