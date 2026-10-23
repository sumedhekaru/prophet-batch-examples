# Figures

Built from the run records by [examples_core/figures.py](../examples_core/figures.py), so they can be regenerated after
rerunning the benchmarks (the records are in each use case's `results/runs/`, which is not committed). The figures here
come from the runs on prophet-batch 0.1.2 from PyPI described in the results pages (2026-10-22/23):

| file | shows | records |
|---|---|---|
| [fig1-speedup.png](fig1-speedup.png) | speed-up vs a 10-process stock pool per dataset (Apple M4), analytic and default history intervals | [walmart](../walmart_grocery_forecasting/results/local-macos-m4.md), [public datasets](../public_datasets/results/macos-m4.md) |
| [fig2-accuracy.png](fig2-accuracy.png) | per-series MASE, stock vs prophet-batch, six datasets | [public datasets](../public_datasets/results/macos-m4.md) |
| [fig3-fit-quality.png](fig3-fit-quality.png) | log-posterior gain over Stan per series (38,905 series) | same |
| [fig4-spark-phases.png](fig4-spark-phases.png) | Spark batch phases, walmart and M5 item × store | [walmart](../walmart_grocery_forecasting/results/dataproc-us-east1.md), [public](../public_datasets/results/dataproc-us-east1.md) |
| [fig5-scaling.png](fig5-scaling.png) | time vs number of series (100 → 30,490) | [scaling](../public_datasets/results/scaling-macos-m4.md) |
| [fig5b-workers.png](fig5b-workers.png) | time vs workers (1 → 10) at 1,000 series | same |
| [fig6-stream-memory.png](fig6-stream-memory.png) | memory over time while 1,000,072 series stream through | [streaming](../streaming_csv/results/macos-m4.md) |

```sh
uv run python -m examples_core.figures --out figures \
  --walmart walmart_grocery_forecasting/results/runs/local-bench-<stamp> \
  --public public_datasets/results/runs/local-bench-<stamp> --small public_datasets/results/runs/local-bench-<stamp> \
  --scaling public_datasets/results/runs/scaling-local-m5_item_store-<stamp>.json \
  --workers public_datasets/results/runs/scaling-workers-local-m5_item_store-<stamp>.json \
  --spark "Walmart, 1,437 items=walmart_grocery_forecasting/results/runs/dataproc-bench-<stamp>" \
  --spark "M5 item × store, 30,490 series=public_datasets/results/runs/dataproc-bench-<stamp>/m5_item_store" \
  --stream streaming_csv/results/runs/m5_item-x328p-<stamp>.json
```

Colours: a categorical palette validated for colour-vision deficiency (blue: prophet-batch, orange: stock Prophet,
green: the two-step path or the default intervals), every series also labelled directly.
