# Spark benchmark: m5_item_store

6 runs · m5_item_store, 30,490 series · Spark 3.5.3 · master `spark://gdpic-srvls-batch-7ba3b60a-8832-43dc-ab56-4d6eec1ffd41-m:7077` · 2 executors, parallelism 8 · shuffle partitions 32 · prophet 1.5.0 · prophet-batch 0.1.2 (PyPI) · examples d5f2058

## Phases (seconds: median, (min–max) over repetitions)

| phase | stock (n=3) | batch (n=3) |
|---|---:|---:|
| provision | 65.7 (65.6–75.4) | 65.6 (65.1–110.8) |
| driver_start | 31.4 (30.1–35.3) | 29.7 (29.4–62.6) |
| executors | 7.6 (7.1–9.1) | 8.6 (3.3–11.1) |
| load | 157.6 (154.8–159.2) | 162.2 (150.2–181.7) |
| warmup | 13.6 (13.0–14.0) | 13.4 (13.1–15.4) |
| execute | 4479.5 (4113.1–4583.5) | 392.0 (347.7–402.9) |
| post | 26.1 (26.1–26.6) | 22.5 (17.6–25.5) |
| shutdown | 8.0 (7.9–8.3) | 6.6 (6.4–6.6) |
| end_to_end | 4787.6 (4437.2–4893.9) | 710.3 (644.1–795.7) |

## Speed-up (stock / prophet-batch, medians)

- **execute**: 11.4× (per repetition: 11.7×, 12.9×, 10.2×)
- **end_to_end**: 6.7× (per repetition: 6.2×, 7.4×, 6.2×)

## Parallelism used (from per-task records)

| method | tasks | hosts | processes | max concurrent | core utilisation during execute |
|---|---:|---:|---:|---:|---:|
| stock | 30490 (30490–30490) | 2 (2–2) | 8 (8–8) | 8 (8–8) | 92.6 (92.5–96.6)% |
| batch | 32 (32–32) | 2 (2–2) | 8 (8–8) | 8 (8–8) | 72.6 (72.3–78.2)% |

## Accuracy and reproducibility

| method | WAPE | MASE | 80% coverage | forecasts identical across repetitions |
|---|---:|---:|---:|---|
| stock | 0.7692 | 1.6443 | 0.785 | True |
| batch | 0.7687 | 1.6428 | 0.784 | True |

## Runs

| run | method | provision | driver_start | executors | load | warmup | execute | post | shutdown | end_to_end |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bench-20261022-224946-m5-item-store-r1-batch | batch | 110.8 | 62.6 | 3.3 | 181.7 | 13.4 | 392.0 | 25.5 | 6.4 | 795.7 |
| bench-20261022-224946-m5-item-store-r1-stock | stock | 65.7 | 31.4 | 7.6 | 157.6 | 14.0 | 4583.5 | 26.1 | 8.0 | 4893.9 |
| bench-20261022-224946-m5-item-store-r2-batch | batch | 65.6 | 29.7 | 8.6 | 150.2 | 13.1 | 347.7 | 22.5 | 6.6 | 644.1 |
| bench-20261022-224946-m5-item-store-r2-stock | stock | 65.6 | 30.1 | 9.1 | 154.8 | 13.6 | 4479.5 | 26.6 | 8.3 | 4787.6 |
| bench-20261022-224946-m5-item-store-r3-batch | batch | 65.1 | 29.4 | 11.1 | 162.2 | 15.4 | 402.9 | 17.6 | 6.6 | 710.3 |
| bench-20261022-224946-m5-item-store-r3-stock | stock | 75.4 | 35.3 | 7.1 | 159.2 | 13.0 | 4113.1 | 26.1 | 7.9 | 4437.2 |
