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

All results on **prophet-batch 0.1.2 from PyPI**, 3 repetitions each, median. Local, Apple M4 (10 cores), 1,437 items,
fit + forecast ([full tables](results/local-macos-m4.md)):

| model | stock, 10-process pool | prophet-batch `forecast_many` | accuracy (Δ MASE, ± 2 SE) |
|---|---:|---:|---:|
| default | 55.5 s | 4.1 s (13.6×) | −0.0018 ± 0.0023 |
| + events | 74.1 s | 5.7 s (13.1×) | −0.0011 ± 0.0021 |
| + events + SNAP | 79.5 s | 6.9 s (11.6×) | −0.0010 ± 0.0022 |

prophet-batch with `history_uncertainty='analytic'` (one argument); with the default (history intervals sampled like
stock) it is 3.9–4.6× faster. `fit_many` + `predict_many` (when you want the fitted models): 9.9× / 10.5× / 8.6×.

| environment | `forecast_many` vs a stock pool on the same cores (default / events / events + SNAP) |
|---|---|
| macOS, Apple M4, 10 processes | 13.6× / 13.1× / 11.6× ([page](results/local-macos-m4.md)) |
| Linux container (Docker, same Mac) | 11.5× / 11.4× / 10.2× ([page](results/docker-linux-arm64.md)) |
| Cloud Run job, 4 vCPU | 13.0× / 12.0× / 10.7× ([page](results/cloudrun-us-east1.md)) |
| Spark, Dataproc Serverless, 2 executors × 4 cores (default model, `fit_many` + `predict_many` per group) | 9.8× in execution, 2.2× end to end incl. ≈ 130 s of platform setup, load and warm-up ([page](results/dataproc-us-east1.md)) |
| Windows laptop, i7-1260P, 16 processes | 15.8× / 13.2× / 12.6× ([page](results/windows-i7-1260p.md)) |

Same accuracy everywhere; prophet-batch's forecasts agree across platforms to floating-point rounding (≈ 10⁻⁹).
Earlier results: [results/history/](results/history/) (0.1.1 and pre-release).

## Run it

[envs/local](envs/local/): `sh walmart_grocery_forecasting/envs/local/run.sh` and a notebook. Code: [pipeline/](pipeline/)
(`data.py` download + loading, `models.py` variants, `forecast.py` stock and prophet-batch runners, `run.py` metrics
and reports, `plots.py`).
