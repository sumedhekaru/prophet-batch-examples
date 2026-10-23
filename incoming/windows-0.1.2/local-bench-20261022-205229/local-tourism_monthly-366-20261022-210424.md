# public_datasets: tourism_monthly, 366 series, 24-step holdout (MS)

2026-10-22T21:04:24 · 12th Gen Intel(R) Core(TM) i7-1260P (16 logical CPUs) · Windows-10-10.0.19045-SP0 · Python 3.12.10 · prophet 1.5.0 · prophet-batch 0.1.2 (PyPI) · examples 6d2f22b

## Speed (fit + forecast of history and the holdout)

| method | workers | fit s | forecast s | total s | vs stock pool |
|---|---:|---:|---:|---:|---:|
| stock_serial (timed on 30, extrapolated) | 1 | 157.5 | 40.5 | 198.0 | 0.2× |
| stock_pool | 16 | 37.3 | 6.8 | 44.1 | 1.0× |
| batch_sampled | 16 | 9.7 | 12.2 | 22.0 | 2.0× |
| batch_analytic | 16 | 9.7 | 10.2 | 19.9 | 2.2× |
| forecast_many_sampled | 16 | 15.5 | 0.0 | 15.5 | 2.8× |
| forecast_many_analytic | 16 | 11.6 | 0.0 | 11.6 | 3.8× |
| batch_sampled | 1 | 4.0 | 18.0 | 21.9 | 2.0× |
| batch_analytic | 1 | 4.0 | 7.4 | 11.3 | 3.9× |

## Accuracy on the held-out steps

| method | WAPE | sMAPE | MASE mean | MASE median | 80% coverage | Δ MASE vs stock (± 2 SE) |
|---|---:|---:|---:|---:|---:|---:|
| stock_pool (n_jobs=16) | 0.1657 | 26.83 | 2.2230 | 1.7948 | 0.522 | – |
| batch_sampled (n_jobs=16) | 0.1699 | 27.00 | 2.2310 | 1.8172 | 0.517 | +0.0080 ± 0.0075 |
| batch_analytic (n_jobs=16) | 0.1699 | 27.00 | 2.2310 | 1.8172 | 0.518 | +0.0080 ± 0.0075 |
| forecast_many_sampled (n_jobs=16) | 0.1699 | 27.00 | 2.2310 | 1.8172 | 0.517 | +0.0080 ± 0.0075 |
| forecast_many_analytic (n_jobs=16) | 0.1699 | 27.00 | 2.2310 | 1.8172 | 0.518 | +0.0080 ± 0.0075 |

## Checks

- batch_sampled: n_jobs=1 (366 series) and n_jobs=16 bit-identical: True
- batch_analytic: n_jobs=1 (366 series) and n_jobs=16 bit-identical: True
- forecast_many_sampled and batch_sampled (n_jobs=16) bit-identical: True
- forecast_many_analytic and batch_analytic (n_jobs=16) bit-identical: True
- log posterior ≥ Stan's (share of series, tol 1e-6): 1.0000
- log posterior gain over Stan (min / median): 0.0111 / 1.05
- series fit by Stan (fallbacks, in the n_jobs=1 run): 0
