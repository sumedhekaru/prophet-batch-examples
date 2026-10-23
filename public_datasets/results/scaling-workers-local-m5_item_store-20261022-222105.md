# Scaling: m5_item_store, time vs worker count

2026-10-22T22:21:05 · Apple M4 (10 logical CPUs) · macOS-26.5.2-arm64-arm-64bit · Python 3.12.13 · prophet 1.5.0 · prophet-batch 0.1.2 (PyPI) · examples d5f2058

Seconds for fit + forecast (history and the holdout), median (min–max) over repetitions; speed-up vs the stock pool at the same point (median of the per-repetition ratios).

| workers | reps | stock, process pool | fit_many + predict_many, sampled | fit_many + predict_many, analytic | forecast_many, sampled | forecast_many, analytic | forecast_many analytic vs pool |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1 | 179.1 | 50.2 | 10.1 | 50.7 | 10.4 | 17.3× |
| 2 | 1 | 94.4 | 27.3 | 6.6 | 26.4 | 5.6 | 16.7× |
| 4 | 1 | 51.0 | 15.6 | 4.5 | 14.5 | 3.4 | 14.8× |
| 6 | 1 | 41.5 | 12.9 | 4.2 | 12.0 | 3.2 | 13.0× |
| 8 | 1 | 36.4 | 11.5 | 4.0 | 10.7 | 3.1 | 11.9× |
| 10 | 1 | 33.4 | 11.0 | 4.1 | 10.0 | 3.0 | 11.2× |

forecast_many equals fit_many + predict_many bit for bit at every point: yes
