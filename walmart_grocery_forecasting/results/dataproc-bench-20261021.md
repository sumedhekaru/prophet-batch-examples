# Spark benchmark: dataproc-bench-20261021-202953

6 runs · 1,437 items · Spark 3.5.3 · master `spark://gdpic-srvls-batch-b49cffdf-8eb0-4665-9233-2b6eb00306a8-m:7077` · 2 executors, parallelism 8 · shuffle partitions 32 · prophet 1.5.0 · prophet-batch d4f7824 · examples b37b566

## Phases (seconds: median, (min–max) over repetitions)

| phase | stock (n=3) | batch (n=3) |
|---|---:|---:|
| provision | 85.9 (85.8–90.9) | 90.7 (90.5–97.7) |
| driver_start | 35.0 (34.5–36.7) | 36.8 (35.9–61.7) |
| executors | 11.1 (10.1–12.1) | 9.1 (8.1–10.6) |
| load | 26.1 (25.7–26.6) | 26.0 (24.8–29.9) |
| execute | 263.5 (258.1–265.9) | 40.3 (37.7–41.7) |
| post | 1.2 (1.1–1.3) | 1.3 (1.1–1.3) |
| shutdown | 5.0 (4.9–5.0) | 5.0 (4.9–5.1) |
| end_to_end | 427.7 (422.1–436.7) | 210.2 (208.4–241.4) |

## Speed-up (stock / prophet-batch, medians)

- **execute**: 6.5× (per repetition: 7.0×, 6.6×, 6.2×)
- **end_to_end**: 2.0× (per repetition: 1.8×, 2.1×, 2.0×)

## Parallelism used (from per-task records)

| method | tasks | hosts | processes | max concurrent | core utilisation during execute |
|---|---:|---:|---:|---:|---:|
| stock | 1437 (1437–1437) | 2 (2–2) | 8 (8–8) | 8 (8–8) | 83.9 (83.9–84.3)% |
| batch | 32 (32–32) | 2 (2–2) | 8 (8–8) | 8 (8–8) | 41.6 (40.1–41.7)% |

## Accuracy and reproducibility

| method | WAPE | MASE | 80% coverage | forecasts identical across repetitions |
|---|---:|---:|---:|---|
| stock | 0.3448 | 1.4281 | 0.721 | True |
| batch | 0.3438 | 1.4261 | 0.720 | True |

## Runs

| run | method | provision | driver_start | executors | load | execute | post | shutdown | end_to_end |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| bench-20261021-202953-r1-batch | batch | 97.7 | 61.7 | 8.1 | 29.9 | 37.7 | 1.3 | 5.0 | 241.4 |
| bench-20261021-202953-r1-stock | stock | 85.8 | 34.5 | 12.1 | 25.7 | 263.5 | 1.2 | 4.9 | 427.7 |
| bench-20261021-202953-r2-batch | batch | 90.7 | 35.9 | 10.6 | 24.8 | 40.3 | 1.3 | 4.9 | 208.4 |
| bench-20261021-202953-r2-stock | stock | 90.9 | 36.7 | 11.1 | 26.1 | 265.9 | 1.1 | 5.0 | 436.7 |
| bench-20261021-202953-r3-batch | batch | 90.5 | 36.8 | 9.1 | 26.0 | 41.7 | 1.1 | 5.1 | 210.2 |
| bench-20261021-202953-r3-stock | stock | 85.9 | 35.0 | 10.1 | 26.6 | 258.1 | 1.3 | 5.0 | 422.1 |
