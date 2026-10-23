# Benchmark: local-bench-20261022-205229

m4_weekly × 1, m4_hourly × 1, tourism_monthly × 1 runs · 12th Gen Intel(R) Core(TM) i7-1260P (16 logical CPUs, 16 available) · Windows-10-10.0.19045-SP0 · Python 3.12.10 · prophet 1.5.0 · prophet-batch 0.1.2 (PyPI) · examples 6d2f22b

## Speed: seconds for all items (fit + forecast), median (min–max) over repetitions

### m4_weekly (359 series, 16 workers)

| method | workers | fit s | forecast s | total s | vs stock pool |
|---|---:|---:|---:|---:|---:|
| stock, serial¹ | 1 | 305.6 | 125.9 | 431.6 | 0.2× |
| stock, process pool | 16 | 88.1 | 18.0 | 106.1 | 1.0× |
| prophet-batch, sampled history intervals | 16 | 16.1 | 24.5 | 40.5 | 2.6× |
| prophet-batch, analytic history intervals | 16 | 16.1 | 14.0 | 30.1 | 3.5× |
| forecast_many (one step), sampled history intervals² | 16 | 26.2 | 0.0 | 26.2 | 4.0× |
| forecast_many (one step), analytic history intervals² | 16 | 16.0 | 0.0 | 16.0 | 6.6× |
| prophet-batch, sampled history intervals | 1 | 10.8 | 48.6 | 59.3 | 1.8× |
| prophet-batch, analytic history intervals | 1 | 10.8 | 8.6 | 19.3 | 5.5× |

### m4_hourly (414 series, 16 workers)

| method | workers | fit s | forecast s | total s | vs stock pool |
|---|---:|---:|---:|---:|---:|
| stock, serial¹ | 1 | 180.3 | 71.1 | 251.4 | 0.3× |
| stock, process pool | 16 | 52.0 | 16.3 | 68.3 | 1.0× |
| prophet-batch, sampled history intervals | 16 | 10.7 | 26.5 | 37.2 | 1.8× |
| prophet-batch, analytic history intervals | 16 | 10.7 | 13.2 | 23.8 | 2.9× |
| forecast_many (one step), sampled history intervals² | 16 | 22.1 | 0.0 | 22.1 | 3.1× |
| forecast_many (one step), analytic history intervals² | 16 | 14.7 | 0.0 | 14.7 | 4.6× |
| prophet-batch, sampled history intervals | 1 | 7.7 | 46.2 | 53.9 | 1.3× |
| prophet-batch, analytic history intervals | 1 | 7.7 | 11.7 | 19.4 | 3.5× |

### tourism_monthly (366 series, 16 workers)

| method | workers | fit s | forecast s | total s | vs stock pool |
|---|---:|---:|---:|---:|---:|
| stock, serial¹ | 1 | 157.5 | 40.5 | 198.0 | 0.2× |
| stock, process pool | 16 | 37.3 | 6.8 | 44.1 | 1.0× |
| prophet-batch, sampled history intervals | 16 | 9.7 | 12.2 | 22.0 | 2.0× |
| prophet-batch, analytic history intervals | 16 | 9.7 | 10.2 | 19.9 | 2.2× |
| forecast_many (one step), sampled history intervals² | 16 | 15.5 | 0.0 | 15.5 | 2.8× |
| forecast_many (one step), analytic history intervals² | 16 | 11.6 | 0.0 | 11.6 | 3.8× |
| prophet-batch, sampled history intervals | 1 | 4.0 | 18.0 | 21.9 | 2.0× |
| prophet-batch, analytic history intervals | 1 | 4.0 | 7.4 | 11.3 | 3.9× |

² fit_many + predict_many in one call: the whole time is shown as fit, forecast as 0.

¹ Timed on a sample (30 items), extrapolated. With different worker counts by repetition, the workers column shows the first repetition's.

## Accuracy on the held-out steps of each dataset (first repetition)

| model | method | WAPE | sMAPE | MASE | Δ MASE vs stock (± 2 SE) | 80% coverage |
|---|---|---:|---:|---:|---:|---:|
| m4_weekly | stock, process pool | 0.1307 | 20.35 | 8.2894 | – | 0.554 |
| m4_weekly | prophet-batch, sampled history intervals | 0.1298 | 19.46 | 8.1845 | -0.1049 ± 0.0552 | 0.549 |
| m4_weekly | prophet-batch, analytic history intervals | 0.1298 | 19.46 | 8.1845 | -0.1049 ± 0.0552 | 0.550 |
| m4_weekly | forecast_many (one step), sampled history intervals² | 0.1298 | 19.46 | 8.1845 | -0.1049 ± 0.0552 | 0.549 |
| m4_weekly | forecast_many (one step), analytic history intervals² | 0.1298 | 19.46 | 8.1845 | -0.1049 ± 0.0552 | 0.550 |
| m4_hourly | stock, process pool | 0.0529 | 18.09 | 1.6309 | – | 0.655 |
| m4_hourly | prophet-batch, sampled history intervals | 0.0548 | 18.20 | 1.6357 | +0.0048 ± 0.0055 | 0.654 |
| m4_hourly | prophet-batch, analytic history intervals | 0.0548 | 18.20 | 1.6357 | +0.0048 ± 0.0055 | 0.652 |
| m4_hourly | forecast_many (one step), sampled history intervals² | 0.0548 | 18.20 | 1.6357 | +0.0048 ± 0.0055 | 0.654 |
| m4_hourly | forecast_many (one step), analytic history intervals² | 0.0548 | 18.20 | 1.6357 | +0.0048 ± 0.0055 | 0.652 |
| tourism_monthly | stock, process pool | 0.1657 | 26.83 | 2.2230 | – | 0.522 |
| tourism_monthly | prophet-batch, sampled history intervals | 0.1699 | 27.00 | 2.2310 | +0.0080 ± 0.0075 | 0.517 |
| tourism_monthly | prophet-batch, analytic history intervals | 0.1699 | 27.00 | 2.2310 | +0.0080 ± 0.0075 | 0.518 |
| tourism_monthly | forecast_many (one step), sampled history intervals² | 0.1699 | 27.00 | 2.2310 | +0.0080 ± 0.0075 | 0.517 |
| tourism_monthly | forecast_many (one step), analytic history intervals² | 0.1699 | 27.00 | 2.2310 | +0.0080 ± 0.0075 | 0.518 |

## Memory per step (main process: working set; workers: not measured on this platform)

| group | step | main process peak GB | largest worker GB | all workers GB |
|---|---|---:|---:|---:|
| m4_weekly | stock_serial | 0.20 | – | – |
| m4_weekly | stock_pool | 0.15 | – | – |
| m4_weekly | batch n_jobs=16 | 0.20 | – | – |
| m4_weekly | forecast_many n_jobs=16 | 0.19 | – | – |
| m4_weekly | batch n_jobs=1 | 0.30 | – | – |
| m4_hourly | stock_serial | 0.16 | – | – |
| m4_hourly | stock_pool | 0.14 | – | – |
| m4_hourly | batch n_jobs=16 | 0.20 | – | – |
| m4_hourly | forecast_many n_jobs=16 | 0.19 | – | – |
| m4_hourly | batch n_jobs=1 | 0.26 | – | – |
| tourism_monthly | stock_serial | 0.13 | – | – |
| tourism_monthly | stock_pool | 0.12 | – | – |
| tourism_monthly | batch n_jobs=16 | 0.15 | – | – |
| tourism_monthly | forecast_many n_jobs=16 | 0.15 | – | – |
| tourism_monthly | batch n_jobs=1 | 0.17 | – | – |

Median (min–max) over repetitions.

## Checks

- m4_weekly: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: one repetition.
- m4_hourly: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: one repetition.
- tourism_monthly: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: one repetition.
