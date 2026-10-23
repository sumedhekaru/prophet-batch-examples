# Scaling on macOS, Apple M4: time vs number of series, and vs workers

2026-10-22 · macOS 26.5.2 arm64 · prophet 1.5.0 and **prophet-batch 0.1.2, both from PyPI** · examples `d5f2058` ·
M5 item × store, default `Prophet()`, fit + forecast of history and the 28 held-out days · samples are nested (the
first n of one seeded permutation, so each point contains the smaller ones) · reproduce:
`uv run python -m public_datasets.pipeline.scaling` and
`uv run python -m public_datasets.pipeline.scaling --points 1000 --reps 1 --workers-sweep 1,2,4,6,8,10`
([pipeline/scaling.py](../pipeline/scaling.py)). Full tables: [series](scaling-local-m5_item_store-20261022-220829.md),
[workers](scaling-workers-local-m5_item_store-20261022-222105.md). At every point, `forecast_many`'s forecasts are
bit-identical to `fit_many` + `predict_many`'s.

## Time vs number of series (10 workers; 3 runs up to 3,000 series, 1 above)

| series | stock, 10-process pool | `fit_many` + `predict_many`, analytic | `forecast_many`, analytic | `forecast_many` vs pool |
|---:|---:|---:|---:|---:|
| 100 | 4.4 s | 2.1 s | 1.2 s | **3.7×** |
| 300 | 10.9 s | 2.5 s | 1.6 s | **6.5×** |
| 1,000 | 33.5 s | 4.3 s | 3.2 s | **10.6×** |
| 3,000 | 99.9 s | 9.4 s | 7.6 s | **13.1×** |
| 10,000 | 320.7 s | 26.9 s | 21.7 s | **14.8×** |
| 30,490 | 982.8 s | 105.0 s | 68.8 s | **14.3×** |

Stock Prophet's time grows linearly (≈ 32 ms per series on the pool), and so does `forecast_many`'s. The gain rises
from 3.7× at 100 series, where starting the worker processes is most of the work, to 13–15× from 3,000 series on. The
two-step path grows faster than linearly at the top (10,000 → 30,490 series: 3.9× the time for 3.05× the series):
30,490 fitted models travel from the workers to the main process and back; `forecast_many` keeps each series' fit and
forecast in one worker.

## Time vs workers (1,000 series, 1 run)

| workers | stock, process pool | `forecast_many`, analytic | `forecast_many` vs pool |
|---:|---:|---:|---:|
| 1 | 179.1 s | 10.4 s | **17.3×** |
| 2 | 94.4 s | 5.6 s | **16.7×** |
| 4 | 51.0 s | 3.4 s | **14.8×** |
| 6 | 41.5 s | 3.2 s | **13.0×** |
| 8 | 36.4 s | 3.1 s | **11.9×** |
| 10 | 33.4 s | 3.0 s | **11.2×** |

On one core prophet-batch is 17× faster: the gain is in the work, not the parallelism. Stock Prophet scales 5.4× from
1 to 10 workers (the M4 has 4 performance and 6 efficiency cores); at 1,000 series prophet-batch levels off after
≈ 4 workers, where its remaining time is fixed costs (on 30,490 series it keeps scaling).
