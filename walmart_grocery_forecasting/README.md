# Walmart grocery forecasting (M5 FOODS, item level)

**Data.** The M5 competition's Walmart sales, FOODS category, with each item summed over the 10 stores: 1,437 daily
series, 2011-01-29 to 2016-05-22 (1,941 days). The last 28 days are held out, the M5 evaluation horizon.

**Model.** The same for every item, three variants ([pipeline/models.py](pipeline/models.py)): default `Prophet()`;
plus M5 calendar events as holidays; plus SNAP days of the three states as regressors.

**Compared.** Stock Prophet (one fit per series: serially, and in a process pool) against prophet-batch (`fit_many` +
`predict_many`), on identical inputs.

**Reported.** Accuracy on the 28 held-out days (WAPE, sMAPE, MASE, 80% interval coverage) and speed (fit + forecast
time), per environment.

**Environments.** [local](envs/local/) first; then [docker](envs/docker/), [cloudrun_job](envs/cloudrun_job/) and
[dataproc](envs/dataproc/), simulated locally with Docker before running on GCP.

## Results

Local, Apple M4 (10 cores), 1,437 items, fit + forecast ([full tables](results/local-macos-m4.md)):

| model | stock, 10-process pool | prophet-batch | accuracy (Δ MASE, ± 2 SE) |
|---|---:|---:|---:|
| default | 58.6 s | 6.5 s (9.1×) | −0.0018 ± 0.0023 |
| + events | 68.6 s | 11.2 s (6.1×) | −0.0011 ± 0.0021 |
| + events + SNAP | 76.9 s | 15.1 s (5.1×) | −0.0010 ± 0.0022 |

prophet-batch with `history_uncertainty='analytic'`; with history intervals sampled like stock it is 2.9–3.5× faster.

## Run it

[envs/local](envs/local/): `sh walmart_grocery_forecasting/envs/local/run.sh` and a notebook. Code: [pipeline/](pipeline/)
(`data.py` download + loading, `models.py` variants, `forecast.py` stock and prophet-batch runners, `run.py` metrics
and reports, `plots.py`).
