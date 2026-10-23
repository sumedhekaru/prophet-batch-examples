# Scaling: m5_item_store, time vs number of series

2026-10-22T22:08:29 · Apple M4 (10 logical CPUs) · macOS-26.5.2-arm64-arm-64bit · Python 3.12.13 · prophet 1.5.0 · prophet-batch 0.1.2 (PyPI) · examples d5f2058

Seconds for fit + forecast (history and the holdout), median (min–max) over repetitions; speed-up vs the stock pool at the same point (median of the per-repetition ratios).

| n | reps | stock, process pool | fit_many + predict_many, sampled | fit_many + predict_many, analytic | forecast_many, sampled | forecast_many, analytic | forecast_many analytic vs pool |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 3 | 4.4 (4.3–4.6) | 2.9 (2.7–2.9) | 2.1 (2.0–2.2) | 1.9 (1.8–2.0) | 1.2 (1.1–1.3) | 3.7× |
| 300 | 3 | 10.9 (10.6–11.1) | 4.6 (4.5–4.9) | 2.5 (2.4–2.7) | 3.8 (3.7–3.8) | 1.6 (1.6–1.8) | 6.5× |
| 1,000 | 3 | 33.5 (33.3–33.9) | 11.3 (10.9–11.7) | 4.3 (4.1–4.3) | 10.0 (9.8–10.2) | 3.2 (3.1–3.4) | 10.6× |
| 3,000 | 3 | 99.9 (96.7–101.8) | 30.3 (29.4–31.2) | 9.4 (9.0–9.9) | 28.4 (27.6–29.7) | 7.6 (7.2–7.9) | 13.1× |
| 10,000 | 1 | 320.7 | 95.6 | 26.9 | 90.7 | 21.7 | 14.8× |
| 30,490 | 1 | 982.8 | 312.5 | 105.0 | 289.7 | 68.8 | 14.3× |

forecast_many equals fit_many + predict_many bit for bit at every point: yes
