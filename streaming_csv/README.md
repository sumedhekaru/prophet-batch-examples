# streaming_csv: forecast a file of any size with flat memory

Real catalogs hold millions of series (store × item, for example); loading them all at once is not the way. The
pattern: read a large batch of series, forecast it, write it out, and keep the three going at the same time. This
example does exactly that with a plain CSV, so the whole pattern is visible and easy to adapt. prophet-batch only
computes: your code reads and writes the data, in whatever format and place you use.

```
reader thread  --[queue: ≤ 2 batches]-->  main thread: Pool.forecast_many  --[queue: ≤ 2]-->  writer thread
pd.read_csv(chunksize=...)                fit + forecast each batch on                      one CSV part per
whole series per chunk                    workers kept for the whole run                    batch (part-00007.csv)
```

```sh
uv run python -m streaming_csv.prepare --copies 4            # the processed input: M5 items, 4 copies (≈ 600 MB)
uv run python -m streaming_csv.run data/streaming/m5_item-x4.csv --series-per-batch 1000
```

**The input** (`prepare.py`): the processed CSV a pipeline would produce upstream, one row per (series, day), each
series' rows together and every series the same length (written next to the file). Knowing that, the reader takes
`rows_per_series × series_per_batch` rows per chunk and every chunk holds whole series. Your own data will have its
own layout; what matters is that a batch never splits a series.

**Memory** stays flat: at most about five batches exist at once (two read ahead, one being forecast, two waiting to
be written), whatever the size of the file. Each run records its memory over time and the peak.

**Restarts:** each batch is written to its own part file (written to a temporary name, then renamed). A part that
exists is not forecast again, so a crashed run picks up where it stopped.

**Output:** `ds, yhat, yhat_lower, yhat_upper` for the forecast horizon, the usual production output. Stock Prophet's
full frame (history rows and every component) is the default of `forecast_many`; this example opts out of it.

**Other storage**, same pattern: Parquet (read row groups or a dataset filter per batch; write one file per batch),
a database (`SELECT ... ORDER BY series_id` through a server-side cursor, `fetchmany`; write with a bulk insert or
`COPY`), or Spark (`mapInPandas` per partition, as in the Dataproc example).

**Results** ([results/macos-m4.md](results/macos-m4.md), prophet-batch 0.1.2 from PyPI, Apple M4): 3,049 → 24,392
series (169 MB → 1.5 GB) with the main process at 0.42 → 0.56 GB; and **1,000,072 series from a 7.4 GB compressed CSV
in 33.4 minutes**, memory bounded at ≈ 1 GB in the main process and 0.14 GB per worker throughout. `prepare.py
--copies N --perturb --gzip` makes such a file (copies after the first resampled into different series); `run.py` and
`check.py` read `.csv.gz` as well, and `check.py --first-series N` checks a file too large to forecast in memory.

Uses `forecast_many` and `Pool` (prophet-batch ≥ 0.1.2, installed from PyPI by `uv sync`).
