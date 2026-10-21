# Local run: macOS, Apple M4 (10 cores)

2026-10-20 · macOS 26.5.2 arm64 · Python 3.12.13 · prophet 1.5.0 (PyPI) · prophet-batch 0.1.0.dev0 (`a891bd0`; the two holiday variants rerun at `c8d9234`) ·
pandas 3.0.6 · numpy 2.5.4 · 1,437 M5 FOODS items, train 1,913 days, 28 days held out · 10 worker processes.
Reproduce: `sh walmart_grocery_forecasting/envs/local/run.sh`.

Every method fits the model and forecasts the history plus the 28 days, as `model.predict(model.make_future_dataframe(28))`
does. prophet-batch: `fit_many` + `predict_many`, with history intervals sampled like stock (`history_uncertainty=True`)
or in exact closed form (`'analytic'`).

## Speed: seconds for all 1,437 items (fit + forecast)

| model | stock, serial¹ | stock, 10-process pool | prophet-batch, sampled history intervals | prophet-batch, analytic history intervals |
|---|---:|---:|---:|---:|
| default `Prophet()` | 302.5 | 58.6 | 16.5 (3.5×) | **6.5 (9.1×)** |
| + M5 events as holidays | 382.8 | 69.7 | 21.9 (3.2×) | **11.3 (6.2×)** |
| + events + SNAP regressors | 402.5 | 75.6 | 23.7 (3.2×) | **13.5 (5.6×)** |

Speed-ups are against the stock 10-process pool. ¹ Timed on 30 items, extrapolated. The SNAP variant needs
`make_model` (for `add_regressor`); since prophet-batch `c8d9234` identical `make_model` configs share their
preprocessing, which took its fit from 5.6 s to 4.0 s (15.1 → 13.5 s in total).

## Accuracy on the 28 held-out days

| model | WAPE stock / batch | sMAPE stock / batch | MASE stock / batch | Δ MASE (± 2 SE) | 80% coverage stock / batch |
|---|---|---|---|---:|---|
| default | 0.3446 / 0.3438 | 48.43 / 48.39 | 1.4279 / 1.4261 | −0.0018 ± 0.0023 | 0.722 / 0.720 |
| events | 0.3479 / 0.3470 | 48.91 / 48.87 | 1.4388 / 1.4377 | −0.0011 ± 0.0021 | 0.712 / 0.710 |
| events + SNAP | 0.3423 / 0.3415 | 48.51 / 48.46 | 1.4238 / 1.4228 | −0.0010 ± 0.0022 | 0.710 / 0.709 |

Same accuracy (every Δ MASE within noise). Coverage: analytic mode; prophet-batch's intervals are slightly narrower
(its fits reach the exact optimum, where Stan's L-BFGS stops early). Adding events alone does not help these items;
events + SNAP gives the lowest WAPE, for both.

## Checks (all variants)

- prophet-batch forecasts are bit-identical with `n_jobs=1` and `n_jobs=10`.
- Every fit's log posterior is at least Stan's (1,437 / 1,437; median gain ≈ 3).
- No series fell back to Stan.
- Setting BLAS threads to 1 (`OMP_NUM_THREADS` etc.) makes no difference to prophet-batch (default: 6.6 s vs 6.5 s).
