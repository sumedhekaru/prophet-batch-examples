> **Superseded (history).** Results on prophet-batch 0.1.1 from PyPI (2026-10-22). Current results, on 0.1.2 with `forecast_many`: [local-macos-m4.md](../local-macos-m4.md).

# Local run: macOS, Apple M4 (10 cores)

2026-10-22 · macOS 26.5.2 arm64 · Python 3.12.13 · prophet 1.5.0 and **prophet-batch 0.1.1, both from PyPI** · pandas
3.0.6 · numpy 2.5.4 · examples `05e472d` · 1,437 M5 FOODS items, train 1,913 days, 28 days held out · 10 worker
processes · **3 repetitions** of every model variant: median (min–max). Reproduce:
`REPS=3 sh walmart_grocery_forecasting/envs/local/run.sh`. Every table: [local-bench-20261022-001238.md](../local-bench-20261022-001238.md).

Every method fits the model and forecasts the history plus the 28 days, as `model.predict(model.make_future_dataframe(28))`
does. prophet-batch: `fit_many` + `predict_many`, with history intervals sampled like stock (`history_uncertainty=True`)
or in exact closed form (`'analytic'`), keeping only the interval columns (`predict_many(columns=...)`), as the stock
workers return only those. Linux container on the same Mac: [docker-linux-arm64.md](docker-linux-arm64-0.1.1.md).

## Speed: seconds for all 1,437 items (fit + forecast), median of 3

| model | stock, serial¹ | stock, 10-process pool | prophet-batch, sampled history intervals | prophet-batch, analytic history intervals |
|---|---:|---:|---:|---:|
| default `Prophet()` | 303.0 | 53.1 | 15.4 (3.4×) | **5.2 (10.2×, 9.9–10.4)** |
| + M5 events as holidays | 384.7 | 69.4 | 16.6 (4.2×) | **6.7 (10.4×, 10.4–10.6)** |
| + events + SNAP regressors | 401.5 | 75.5 | 18.4 (4.1×) | **8.5 (8.9×, 8.5–8.9)** |

Speed-ups are against the stock 10-process pool of the same run. ¹ Timed on 30 items, extrapolated.

## Accuracy on the 28 held-out days

| model | WAPE stock / batch | sMAPE stock / batch | MASE stock / batch | Δ MASE (± 2 SE) | 80% coverage stock / batch |
|---|---|---|---|---:|---|
| default | 0.3446 / 0.3438 | 48.43 / 48.39 | 1.4279 / 1.4261 | −0.0018 ± 0.0023 | 0.722 / 0.720 |
| events | 0.3479 / 0.3470 | 48.91 / 48.87 | 1.4388 / 1.4377 | −0.0011 ± 0.0021 | 0.712 / 0.710 |
| events + SNAP | 0.3423 / 0.3415 | 48.51 / 48.46 | 1.4238 / 1.4228 | −0.0010 ± 0.0022 | 0.710 / 0.709 |

Same accuracy (every Δ MASE within noise). Coverage: analytic mode; prophet-batch's intervals are slightly narrower
(its fits reach the exact optimum, where Stan's L-BFGS stops early). Adding events alone does not help these items;
events + SNAP gives the lowest WAPE, for both.

## Checks (every run)

- prophet-batch forecasts are bit-identical with `n_jobs=1` and `n_jobs=10`.
- Every fit's log posterior is at least Stan's (1,437 / 1,437).
- No series fell back to Stan.
- Forecasts are identical across the 3 repetitions, for stock and prophet-batch.

History: the pre-release run (prophet-batch 0.1.0.dev0 from a local checkout) gave 10.2× / 10.3× / 8.6× and the
same accuracy: [history/local-macos-m4.md](local-macos-m4-prerelease.md), with how dogfooding got it there.
