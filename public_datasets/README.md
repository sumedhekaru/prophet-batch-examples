# public_datasets: six public forecasting datasets, stock Prophet vs prophet-batch

Default `Prophet()` on six public datasets (38,905 series in all), each split by its own convention, forecasting the
history plus the held-out steps (typical usage, so history intervals are included). Stock Prophet runs per series,
serially (a sample, extrapolated) and in a process pool on every core; prophet-batch runs `forecast_many` (one call)
and `fit_many` + `predict_many` (when you want the fitted models).

| dataset | series | rows per series | frequency | held out | source |
|---|---:|---:|---|---:|---|
| `m5_item_store` | 30,490 | 1,941 | daily | 28 days | Walmart M5 ([Nixtla's m5.zip](https://github.com/Nixtla/m5-forecasts)), item × store |
| `m4_daily` | 4,227 | ≈ 2,371 | daily | 14 days | [M4 competition](https://github.com/Mcompetitions/M4-methods), official split |
| `m5_item` | 3,049 | 1,941 | daily | 28 days | Walmart M5, each item summed over the 10 stores |
| `m4_weekly` | 359 | ≈ 1,035 | weekly | 13 weeks | M4 |
| `m4_hourly` | 414 | ≈ 902 | hourly | 48 hours | M4 |
| `tourism_monthly` | 366 | ≈ 299 | monthly | 24 months | [Monash archive](https://zenodo.org/records/4656096) |

The three large datasets show speed at scale (many series; long series); the three small ones are there for accuracy
across frequencies (they finish in seconds, where process start-up dominates). Every file is pinned by SHA-256
([pipeline/data.py](pipeline/data.py)); the splits are the same as the parallel-prophet benchmark (D3).

Reported per dataset: accuracy (WAPE, sMAPE, MASE mean and median, 80% interval coverage, Δ MASE vs stock ± 2 SE),
fit quality (each series' log posterior vs Stan's), speed (fit + forecast), and checks (prophet-batch with `n_jobs=1`
bit-identical to `n_jobs=many`; on more than 5,000 series on a 2,000-series sample, valid because a series' fit
does not depend on its batch mates; fallbacks to Stan).

## Results

All on **prophet-batch 0.1.2 from PyPI**; the large datasets 3 times, median. Fit + forecast of every series, against
stock Prophet in a process pool on the same cores, `forecast_many` with `history_uncertainty='analytic'`:

| environment | M5 item × store (30,490) | M4 Daily (4,227) | M5 item (3,049) |
|---|---:|---:|---:|
| macOS, Apple M4, 10 processes ([page](results/macos-m4.md)) | 14.5× (993 s → 68 s) | 37.1× (489 s → 13 s) | 14.8× |
| Linux container, same Mac ([page](results/docker-linux-arm64.md)) | 12.3× | 28.6× | 13.0× |
| Cloud Run job, 8 vCPU ([page](results/cloudrun-us-east1.md)) | 13.8× | 27.7× | 13.5× |
| Spark, Dataproc, 2 × 4 cores, end to end / execute ([page](results/dataproc-us-east1.md)) | 6.7× / 11.4× | 6.6× / 18.6× | 3.2× / 10.9× |

With the default (history intervals sampled like stock), 3.6× / 9.5× / 3.8× on the Mac. The small datasets (359–414
series, seconds of work) gain 2.7–8.0×. **Accuracy:** as good as stock on all six datasets, better beyond noise on
four; prophet-batch's fit (log posterior) is at least Stan's on 38,905 of 38,905 series. **Scaling:** the gain grows
from 3.7× at 100 series to 13–15× from 3,000 series on, and it is 17× on a single core
([scaling](results/scaling-macos-m4.md)).

## Run it

```sh
uv run python -m public_datasets.pipeline.data                                   # download + verify (≈ 120 MB)
sh public_datasets/envs/local/run.sh                                             # the three large datasets
DATASETS="m4_weekly m4_hourly tourism_monthly" sh public_datasets/envs/local/run.sh
REPS=3 sh public_datasets/envs/local/run.sh                                      # benchmark: 3 repetitions + summary.md
sh public_datasets/envs/docker/build.sh && REPS=3 sh public_datasets/envs/docker/run.sh   # the same in Linux
uv run python -m public_datasets.pipeline.scaling                                # time vs number of series
```

In the cloud: [Cloud Run job](envs/cloudrun_job/README.md) and [Spark on Dataproc](envs/dataproc/README.md).
`m5_item_store` needs ≈ 11–14 GB of memory for the full comparison (the run keeps every method's results). Code:
[pipeline/](pipeline/) (data, run, scaling, spark_job); the runners, metrics and run records are shared with the
other use cases ([examples_core/](../examples_core/)).
