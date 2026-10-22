# Walmart grocery forecasting (M5 FOODS, item level)

**Data.** The M5 competition's Walmart sales, FOODS category, with each item summed over the 10 stores: 1,437 daily
series, 2011-01-29 to 2016-05-22 (1,941 days). The last 28 days are held out, the M5 evaluation horizon.

**Model.** The same for every item, three variants ([pipeline/models.py](pipeline/models.py)): default `Prophet()`;
plus M5 calendar events as holidays; plus SNAP days of the three states as regressors.

**Compared.** Stock Prophet (one fit per series: serially, and in a process pool) against prophet-batch (`fit_many` +
`predict_many`), on identical inputs.

**Reported.** Accuracy on the 28 held-out days (WAPE, sMAPE, MASE, 80% interval coverage) and speed (fit + forecast
time), per environment.

**Environments.** [local](envs/local/), [docker](envs/docker/), [cloudrun_job](envs/cloudrun_job/) and
[dataproc](envs/dataproc/) (Spark) run.

## Results

All results on **prophet-batch 0.1.1 from PyPI**, 3 repetitions each, median. Local, Apple M4 (10 cores), 1,437 items,
fit + forecast ([full tables](results/local-macos-m4.md)):

| model | stock, 10-process pool | prophet-batch | accuracy (Δ MASE, ± 2 SE) |
|---|---:|---:|---:|
| default | 53.1 s | 5.2 s (10.2×) | −0.0018 ± 0.0023 |
| + events | 69.4 s | 6.7 s (10.4×) | −0.0011 ± 0.0021 |
| + events + SNAP | 75.5 s | 8.5 s (8.9×) | −0.0010 ± 0.0022 |

prophet-batch with `history_uncertainty='analytic'`; with history intervals sampled like stock it is 3.4–4.2× faster.

| environment | speed-up vs a stock pool on the same cores (default / events / events + SNAP) |
|---|---|
| macOS, Apple M4, 10 processes | 10.2× / 10.4× / 8.9× ([page](results/local-macos-m4.md)) |
| Linux container (Docker, same Mac) | 8.6× / 8.3× / 7.4× ([page](results/docker-linux-arm64.md)) |
| Cloud Run job, 4 vCPU | 10.9× / 11.1× / 8.9× ([page](results/cloudrun-us-east1.md)) |
| Spark, Dataproc Serverless, 2 executors × 4 cores (default model) | 9.7× in execution, 1.9× end to end incl. ≈ 185 s of platform setup, load and warm-up ([page](results/dataproc-us-east1.md)) |
| Windows laptop, i7-1260P, 16 processes (default model) | 11.5× in one run of the 0.1.1 fix before its release (pre-release; a 3-repetition run on 0.1.1 from PyPI is to come) |

Same accuracy everywhere; prophet-batch's forecasts agree across macOS and Linux to 3.5·10⁻⁹, stock Prophet's differ by
up to 11 units/day. Pre-release results (prophet-batch from a local checkout, before PyPI): [results/history/](results/history/).

## Run it

[envs/local](envs/local/): `sh walmart_grocery_forecasting/envs/local/run.sh` and a notebook. Code: [pipeline/](pipeline/)
(`data.py` download + loading, `models.py` variants, `forecast.py` stock and prophet-batch runners, `run.py` metrics
and reports, `plots.py`).
