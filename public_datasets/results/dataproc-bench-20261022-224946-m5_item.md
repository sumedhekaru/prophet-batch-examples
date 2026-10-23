# Spark benchmark: m5_item

6 runs · m5_item, 3,049 series · Spark 3.5.3 · master `spark://gdpic-srvls-batch-75bf6b0e-4662-4a48-929d-512b7e7b8f81-m:7077` · 2 executors, parallelism 8 · shuffle partitions 32 · prophet 1.5.0 · prophet-batch 0.1.2 (PyPI) · examples d5f2058

## Phases (seconds: median, (min–max) over repetitions)

| phase | stock (n=3) | batch (n=3) |
|---|---:|---:|
| provision | 67.1 (64.2–70.4) | 69.8 (65.2–70.5) |
| driver_start | 29.8 (29.7–30.1) | 30.1 (29.3–30.8) |
| executors | 8.6 (8.1–10.1) | 8.6 (8.6–11.1) |
| load | 34.8 (34.3–37.7) | 35.6 (35.5–36.2) |
| warmup | 14.5 (13.6–15.2) | 14.2 (13.9–14.4) |
| execute | 505.3 (502.5–510.2) | 46.4 (44.9–50.1) |
| post | 4.8 (4.7–4.9) | 4.4 (4.4–4.7) |
| shutdown | 4.6 (4.4–6.3) | 4.7 (4.4–4.8) |
| end_to_end | 670.1 (663.0–682.7) | 212.7 (209.9–220.2) |

## Speed-up (stock / prophet-batch, medians)

- **execute**: 10.9× (per repetition: 10.2×, 10.8×, 11.3×)
- **end_to_end**: 3.2× (per repetition: 3.1×, 3.2×, 3.2×)

## Parallelism used (from per-task records)

| method | tasks | hosts | processes | max concurrent | core utilisation during execute |
|---|---:|---:|---:|---:|---:|
| stock | 3049 (3049–3049) | 2 (2–2) | 8 (8–8) | 8 (8–8) | 90.5 (90.2–90.5)% |
| batch | 32 (32–32) | 2 (2–2) | 8 (8–8) | 8 (8–8) | 69.0 (68.1–69.1)% |

## Accuracy and reproducibility

| method | WAPE | MASE | 80% coverage | forecasts identical across repetitions |
|---|---:|---:|---:|---|
| stock | 0.3554 | 1.3647 | 0.723 | True |
| batch | 0.3546 | 1.3626 | 0.721 | True |

## Runs

| run | method | provision | driver_start | executors | load | warmup | execute | post | shutdown | end_to_end |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bench-20261022-224946-m5-item-r1-batch | batch | 70.5 | 29.3 | 11.1 | 35.6 | 14.4 | 50.1 | 4.4 | 4.7 | 220.2 |
| bench-20261022-224946-m5-item-r1-stock | stock | 70.4 | 29.8 | 10.1 | 37.7 | 15.2 | 510.2 | 4.8 | 4.4 | 682.7 |
| bench-20261022-224946-m5-item-r2-batch | batch | 65.2 | 30.1 | 8.6 | 36.2 | 14.2 | 46.4 | 4.7 | 4.4 | 209.9 |
| bench-20261022-224946-m5-item-r2-stock | stock | 64.2 | 30.1 | 8.6 | 34.8 | 13.6 | 502.5 | 4.7 | 4.6 | 663.0 |
| bench-20261022-224946-m5-item-r3-batch | batch | 69.8 | 30.8 | 8.6 | 35.5 | 13.9 | 44.9 | 4.4 | 4.8 | 212.7 |
| bench-20261022-224946-m5-item-r3-stock | stock | 67.1 | 29.7 | 8.1 | 34.3 | 14.5 | 505.3 | 4.9 | 6.3 | 670.1 |
