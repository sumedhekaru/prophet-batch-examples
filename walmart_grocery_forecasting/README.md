# Walmart grocery forecasting (M5 FOODS, item level)

**Data.** The M5 competition's Walmart sales, FOODS category, with each item summed over the 10 stores: 1,437 daily
series, 2011-01-29 to 2016-05-22 (1,941 days). The last 28 days are held out, the M5 evaluation horizon.

**Model.** Default `Prophet()` for every item (variants later: M5 calendar events as holidays, SNAP days as a
regressor).

**Compared.** Stock Prophet (one fit per series: serially, and in a process pool) against prophet-batch (`fit_many` +
`predict_many`), on identical inputs.

**Reported.** Accuracy on the 28 held-out days (WAPE, sMAPE, MASE, 80% interval coverage) and speed (fit + forecast
time), per environment.

**Environments.** [local](envs/local/) first; then [docker](envs/docker/), [cloudrun_job](envs/cloudrun_job/) and
[dataproc](envs/dataproc/), simulated locally with Docker before running on GCP.

Status: planned. See [results/](results/) once runs exist.
