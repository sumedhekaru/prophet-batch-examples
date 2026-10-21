# Spark benchmark: dataproc-bench-20261021-213536

6 runs · 1,437 items · Spark 3.5.3 · master `spark://gdpic-srvls-batch-5a219360-3f03-407f-9de7-ffd0c479508a-m:7077` · 2 executors, parallelism 8 · shuffle partitions 32 · prophet 1.5.0 · prophet-batch d4f7824 · examples 3d0d154

## Phases (seconds: median, (min–max) over repetitions)

| phase | stock (n=3) | batch (n=3) |
|---|---:|---:|
| provision | 86.3 (79.9–90.2) | 85.4 (79.7–88.3) |
| driver_start | 34.5 (34.5–35.4) | 36.5 (34.7–54.1) |
| executors | 10.1 (9.6–10.1) | 10.1 (9.1–10.6) |
| load | 25.2 (24.9–25.9) | 27.7 (24.6–28.4) |
| warmup | 16.4 (15.8–16.6) | 17.1 (16.3–18.9) |
| execute | 255.1 (248.1–260.1) | 26.5 (25.9–33.0) |
| post | 4.5 (4.5–4.8) | 4.5 (4.4–5.0) |
| shutdown | 4.7 (3.6–6.3) | 4.9 (4.8–5.3) |
| end_to_end | 436.5 (432.9–438.0) | 210.5 (206.2–239.2) |

## Speed-up (stock / prophet-batch, medians)

- **execute**: 9.6× (per repetition: 7.7×, 9.6×, 9.8×)
- **end_to_end**: 2.1× (per repetition: 1.8×, 2.1×, 2.1×)

## Parallelism used (from per-task records)

| method | tasks | hosts | processes | max concurrent | core utilisation during execute |
|---|---:|---:|---:|---:|---:|
| stock | 1437 (1437–1437) | 2 (2–2) | 8 (8–8) | 8 (8–8) | 88.6 (87.2–88.9)% |
| batch | 32 (32–32) | 2 (2–2) | 8 (8–8) | 8 (8–8) | 64.6 (56.3–65.2)% |

## Accuracy and reproducibility

| method | WAPE | MASE | 80% coverage | forecasts identical across repetitions |
|---|---:|---:|---:|---|
| stock | 0.3448 | 1.4281 | 0.721 | True |
| batch | 0.3438 | 1.4261 | 0.720 | True |

## Runs

| run | method | provision | driver_start | executors | load | warmup | execute | post | shutdown | end_to_end |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bench-20261021-213536-r1-batch | batch | 85.4 | 54.1 | 10.6 | 27.7 | 18.9 | 33.0 | 4.5 | 4.9 | 239.2 |
| bench-20261021-213536-r1-stock | stock | 86.3 | 35.4 | 9.6 | 25.9 | 16.4 | 255.1 | 4.5 | 4.7 | 438.0 |
| bench-20261021-213536-r2-batch | batch | 79.7 | 36.5 | 9.1 | 28.4 | 16.3 | 25.9 | 5.0 | 5.3 | 206.2 |
| bench-20261021-213536-r2-stock | stock | 90.2 | 34.5 | 10.1 | 25.2 | 16.6 | 248.1 | 4.5 | 3.6 | 432.9 |
| bench-20261021-213536-r3-batch | batch | 88.3 | 34.7 | 10.1 | 24.6 | 17.1 | 26.5 | 4.4 | 4.8 | 210.5 |
| bench-20261021-213536-r3-stock | stock | 79.9 | 34.5 | 10.1 | 24.9 | 15.8 | 260.1 | 4.8 | 6.3 | 436.5 |
