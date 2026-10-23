# Future rows only: stock Prophet's fastest setup vs prophet-batch

2026-10-23T09:20:07 · Apple M4 (10 logical CPUs) · macOS-26.5.2-arm64-arm-64bit · prophet 1.5.0 · prophet-batch 0.1.2 (PyPI) · examples 03e002a · 10 workers · 3 runs: median (min–max)

| dataset | series | stock pool, future rows only | `forecast_many(include_history=False)` | faster | MASE stock / prophet-batch | Δ MASE (± 2 SE) | 80% coverage stock / prophet-batch |
|---|---:|---:|---:|---:|---|---:|---|
| m5_item_store | 30,490 | 626.7 s (618.4–649.9) | 53.6 s (53.5–58.9) | **11.5×** (11.0–11.7) | 1.6442 / 1.6428 | -0.0014 ± 0.0003 | 0.784 / 0.784 |
| m4_daily | 4,227 | 410.8 s (409.2–416.0) | 10.5 s (10.5–10.7) | **38.9×** (38.3–39.4) | 11.9713 / 11.8888 | -0.0826 ± 0.0341 | 0.420 / 0.414 |
| m5_item | 3,049 | 72.4 s (71.7–72.6) | 6.3 s (6.2–6.4) | **11.4×** (11.3–11.6) | 1.3648 / 1.3626 | -0.0022 ± 0.0013 | 0.723 / 0.721 |
