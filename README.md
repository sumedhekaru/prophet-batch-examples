# prophet-batch-examples

Realistic, runnable use cases for [prophet-batch](https://github.com/sumedhekaru/prophet-batch): fitting and
forecasting many [Prophet](https://github.com/facebook/prophet) models at once. Each use case reports **accuracy and
speed** against stock Prophet on the same data, in the environments people actually run: a laptop, Docker, Cloud Run
jobs, Dataproc and Spark.

The story behind these results: [Up to 37× faster Prophet: fitting thousands of series in one call](https://medium.com/@sumedhekaru/up-to-37-faster-prophet-fitting-thousands-of-series-in-one-call-f532fae5c9e7) (Medium).

Running these is also how prophet-batch gets tested in practice. Bugs found here are reported to the repository they
belong to (prophet-batch, or Prophet itself) and fixed there.

Status: in development. The use cases run locally, in a local Linux container, as Cloud Run jobs and on Spark (Dataproc
Serverless); results on prophet-batch 0.1.2 from PyPI. Figures: [figures/](figures/). The examples now install
0.1.3, whose default history intervals (same distribution, drawn from order statistics) make the default-settings
rows as fast as the analytic ones; the analytic rows are unchanged.

## Use cases

| Folder | Data | Question |
|---|---|---|
| [walmart_grocery_forecasting](walmart_grocery_forecasting/) | M5 (Walmart), FOODS category, item level: 1,437 daily series | 28-day forecasts: same accuracy as stock Prophet, 10–16× faster than a stock process pool on the same cores (macOS, Linux, Windows, Cloud Run); on Spark 9.8× in execution |
| [public_datasets](public_datasets/) | M5 item and item × store, M4 Daily / Weekly / Hourly, Tourism Monthly: 38,905 series | Same accuracy (better beyond noise on four datasets) and a fit at least as good as Stan's on every series; 14.5× on 30,490 series and 37× on M4 Daily's long series, 2.7–8× on the three small datasets (Apple M4); on Spark the end-to-end gain grows to 6.7× with the job |
| [streaming_csv](streaming_csv/) | M5 items written as one CSV (1–8 copies, up to 1.5 GB; and 1,000,072 resampled series, 7.4 GB gzip) | A file of any size forecast in batches, read / forecast / write at the same time, with bounded memory and restartable output: a million series in 33 minutes on a laptop |

## Layout

```
README.md                          # this file
examples_core/                     # shared by every use case: stock and prophet-batch runners, metrics, run records,
                                   # bench_summary (repetitions → medians)
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
uv sync          # Python 3.12, prophet==1.5.0 and prophet-batch==0.1.3 from PyPI, jupyter
```

Developing prophet-batch itself: with a checkout of it next to this repo, `PROPHET_BATCH_LOCAL=../prophet-batch` runs
the scripts against that checkout instead (`uv run --with-editable` locally, a wheel built from it in the images).
Each run record says which was used: `prophet-batch 0.1.3 (PyPI)` or `prophet-batch 0.1.3 (local <commit>)`.

## Principles

- Data is downloaded by a script and verified by checksum; it is never committed.
- Every result records the machine, environment and package versions, and can be rerun with one command.
- Published results use released prophet-batch from PyPI (the run records say e.g. "prophet-batch 0.1.2 (PyPI)");
  results from unreleased code are not published here.
- Stock Prophet and prophet-batch get identical inputs and model settings.
