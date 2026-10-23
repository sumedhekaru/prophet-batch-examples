# Future rows only: against stock Prophet's fastest setup (macOS, Apple M4)

2026-10-23 · macOS 26.5.2 arm64 · prophet 1.5.0 and **prophet-batch 0.1.2, both from PyPI** · examples `850b18b`
(record: `03e002a`, a later commit that changed only figures) · 10 workers · the three large datasets, **3 runs**
each: median (min–max). Reproduce: `uv run python -m public_datasets.pipeline.future_only`
([pipeline/future_only.py](../pipeline/future_only.py)). Run record: [future-only-local-20261023-092007.md](future-only-local-20261023-092007.md).

The main comparison ([macos-m4.md](macos-m4.md)) forecasts the history plus the held-out steps, as
`model.predict(model.make_future_dataframe(h))` does, and most of stock Prophet's predict time then goes into
simulating intervals for every history row. A user who only needs the future can ask stock Prophet for the future
rows only (`make_future_dataframe(h, include_history=False)`): stock's fastest setup. Here both methods do exactly
that: a stock process pool forecasting the future rows only, and `forecast_many(..., include_history=False)` with
default settings otherwise (same rows, same interval columns). Both fit every series in full.

| dataset | series | stock pool, future rows only | `forecast_many(include_history=False)` | faster |
|---|---:|---:|---:|---:|
| M5 item × store | 30,490 | 626.7 s (618.4–649.9) | 53.6 s (53.5–58.9) | **11.5×** (11.0–11.7) |
| M4 Daily | 4,227 | 410.8 s (409.2–416.0) | 10.5 s (10.5–10.7) | **38.9×** (38.3–39.4) |
| M5 item | 3,049 | 72.4 s (71.7–72.6) | 6.3 s (6.2–6.4) | **11.4×** (11.3–11.6) |

Against stock's fastest setup the gain is 11–39×, about what analytic history intervals give against the full
forecast (14.5× / 37.1× / 14.8×): it is the fit, not the history intervals, that makes most of the difference.
Accuracy is the same as in the main comparison (MASE stock / prophet-batch: 1.6442 / 1.6428, 11.9713 / 11.8888,
1.3648 / 1.3626; 80% coverage within 0.006).
