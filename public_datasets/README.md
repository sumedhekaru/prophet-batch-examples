# public_datasets: six public forecasting datasets, stock Prophet vs prophet-batch

Default `Prophet()` on six public datasets (38,905 series in all), each split by its own convention, forecasting the
history plus the held-out steps (typical usage, so history intervals are included). Stock Prophet runs per series,
serially (a sample, extrapolated) and in a process pool on every core; prophet-batch runs `fit_many` + `predict_many`.

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

## Run it

```sh
uv run python -m public_datasets.pipeline.data                                   # download + verify (≈ 120 MB)
sh public_datasets/envs/local/run.sh                                             # the three large datasets
DATASETS="m4_weekly m4_hourly tourism_monthly" sh public_datasets/envs/local/run.sh
REPS=3 sh public_datasets/envs/local/run.sh                                      # benchmark: 3 repetitions + summary.md
sh public_datasets/envs/docker/build.sh && REPS=3 sh public_datasets/envs/docker/run.sh   # the same in Linux
```

`m5_item_store` needs ≈ 10 GB of memory with 10 workers. Code: [pipeline/](pipeline/) (data, run); the runners,
metrics and run records are shared with the other use case ([examples_core/](../examples_core/)).

## Results

To come (prophet-batch 0.1.1 from PyPI, 3 repetitions): [results/](results/).
