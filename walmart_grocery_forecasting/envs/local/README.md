# Local run (macOS, Linux, Windows)

From the repo root, after `uv sync` (see the [root README](../../../README.md)):

```sh
sh walmart_grocery_forecasting/envs/local/run.sh          # data + all three model variants, all 1,437 items
sh walmart_grocery_forecasting/envs/local/run.sh --n 50   # quick check on 50 random items
uv run jupyter lab walmart_grocery_forecasting/envs/local/walmart_grocery_forecasting.ipynb
```

Each run writes `walmart_grocery_forecasting/results/runs/local-<model>-<n>-<timestamp>.{json,npz,md}` (gitignored);
the summary of the reference run is committed under [results/](../../results/). Options:
`uv run python -m walmart_grocery_forecasting.pipeline.run --help`.

## Per-OS notes

- **macOS** (reference machine: Apple M4, 10 cores). Nothing extra. Stock Prophet's PyPI wheel ships its own CmdStan.
- **Linux.** Same commands. On a shared server, set `--workers` to the cores you may use (the default is all CPUs).
- **Windows.** `run.sh` needs a POSIX shell (Git Bash or WSL). In PowerShell, run the steps directly:

  ```powershell
  uv run python -m walmart_grocery_forecasting.pipeline.data
  foreach ($m in 'default', 'events', 'events_snap') { uv run python -m walmart_grocery_forecasting.pipeline.run --model $m }
  ```

  prophet-batch's worker processes use `spawn` on every OS, so in your own scripts call `fit_many` / `predict_many`
  with `n_jobs != 1` under `if __name__ == '__main__':`.

Only macOS has been run so far; the Linux path is exercised by the Docker images (later).
