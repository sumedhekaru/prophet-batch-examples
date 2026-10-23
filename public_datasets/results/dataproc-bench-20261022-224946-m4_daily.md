# Spark benchmark: m4_daily

6 runs · m4_daily, 4,227 series · Spark 3.5.3 · master `spark://gdpic-srvls-batch-f5d72ab9-14f9-4da0-b3f7-f00bdd15f7a6-m:7077` · 2 executors, parallelism 8 · shuffle partitions 32 · prophet 1.5.0 · prophet-batch 0.1.2 (PyPI) · examples d5f2058

## Phases (seconds: median, (min–max) over repetitions)

| phase | stock (n=3) | batch (n=3) |
|---|---:|---:|
| provision | 65.8 (59.8–69.4) | 70.4 (65.7–71.7) |
| driver_start | 29.8 (29.6–29.8) | 30.6 (29.7–32.7) |
| executors | 8.6 (7.6–9.1) | 8.6 (8.2–9.6) |
| load | 45.0 (44.0–45.5) | 48.6 (45.7–51.9) |
| warmup | 13.9 (12.9–14.2) | 14.3 (14.2–14.6) |
| execute | 1635.4 (1608.8–1732.6) | 88.0 (86.6–95.4) |
| post | 5.2 (5.1–5.5) | 5.1 (5.0–5.8) |
| shutdown | 5.2 (5.0–5.4) | 5.2 (5.1–5.5) |
| end_to_end | 1809.3 (1774.4–1909.5) | 275.1 (266.3–276.5) |

## Speed-up (stock / prophet-batch, medians)

- **execute**: 18.6× (per repetition: 18.6×, 18.2×, 18.6×)
- **end_to_end**: 6.6× (per repetition: 6.8×, 6.9×, 6.4×)

## Parallelism used (from per-task records)

| method | tasks | hosts | processes | max concurrent | core utilisation during execute |
|---|---:|---:|---:|---:|---:|
| stock | 4227 (4227–4227) | 2 (2–2) | 8 (8–8) | 8 (8–8) | 94.1 (92.0–94.3)% |
| batch | 32 (32–32) | 2 (2–2) | 8 (8–8) | 8 (8–8) | 72.8 (69.4–74.5)% |

## Accuracy and reproducibility

| method | WAPE | MASE | 80% coverage | forecasts identical across repetitions |
|---|---:|---:|---:|---|
| stock | 0.1057 | 11.9655 | 0.419 | True |
| batch | 0.1052 | 11.8888 | 0.414 | True |

## Runs

| run | method | provision | driver_start | executors | load | warmup | execute | post | shutdown | end_to_end |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bench-20261022-224946-m4-daily-r1-batch | batch | 65.7 | 30.6 | 8.6 | 48.6 | 14.6 | 88.0 | 5.1 | 5.1 | 266.3 |
| bench-20261022-224946-m4-daily-r1-stock | stock | 65.8 | 29.6 | 8.6 | 45.5 | 13.9 | 1635.4 | 5.5 | 5.0 | 1809.3 |
| bench-20261022-224946-m4-daily-r2-batch | batch | 71.7 | 29.7 | 9.6 | 45.7 | 14.3 | 95.4 | 5.0 | 5.2 | 276.5 |
| bench-20261022-224946-m4-daily-r2-stock | stock | 69.4 | 29.8 | 9.1 | 44.0 | 14.2 | 1732.6 | 5.2 | 5.2 | 1909.5 |
| bench-20261022-224946-m4-daily-r3-batch | batch | 70.4 | 32.7 | 8.2 | 51.9 | 14.2 | 86.6 | 5.8 | 5.5 | 275.1 |
| bench-20261022-224946-m4-daily-r3-stock | stock | 59.8 | 29.8 | 7.6 | 45.0 | 12.9 | 1608.8 | 5.1 | 5.4 | 1774.4 |
