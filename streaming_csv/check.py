"""Check a streaming run: its parts together equal one in-memory forecast_many of the whole CSV.

    uv run python -m streaming_csv.check data/streaming/m5_item-x1.csv     # reads data/streaming/m5_item-x1-out/
    uv run python -m streaming_csv.check data/streaming/m5_item-x328p.csv.gz --first-series 20000   # a large file

--first-series N compares the first N series only (the reference is an in-memory forecast_many, so the whole of a
very large file would not fit) and checks that the parts hold every series of the file, in order, once.

Same arguments as run.py's forecast (seed 0, horizon only, four columns). Point forecasts and intervals are compared
after the CSV round trip of the parts (text with full float precision), so they match to the last printed digit.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from examples_core.records import available_cpus, utf8_stdout

from .prepare import base_name, meta_path
from .run import COLUMNS


def main() -> int:
    utf8_stdout()  # the result line has a "→"; a Windows console's code page can't print it
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('csv', type=Path)
    p.add_argument('--out', type=Path, default=None)
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--first-series', type=int, default=0, help='compare the first N series only (default: all)')
    a = p.parse_args()
    from prophet_batch import forecast_many

    meta = json.loads(meta_path(a.csv).read_text())
    out_dir = a.out or a.csv.with_name(base_name(a.csv) + '-out')
    files = sorted(out_dir.glob('part-*.csv'))
    first = a.first_series if 0 < a.first_series < meta['series'] else 0
    if first:
        # every series of the file in the parts, once, in the file's order (ids from the parts' unique_id column)
        ids = pd.concat([pd.read_csv(f, usecols=['unique_id'])['unique_id'] for f in files], ignore_index=True)
        counts = ids.value_counts()
        complete = (len(ids) == meta['series'] * meta['horizon'] and len(counts) == meta['series']
                    and bool((counts == meta['horizon']).all()))
        print(f"parts: {len(files):,} files, {len(counts):,} series × {meta['horizon']} rows "
              f"(file: {meta['series']:,} series) → {'complete' if complete else 'INCOMPLETE'}")
        df = pd.read_csv(a.csv, parse_dates=['ds'], nrows=first * meta['rows_per_series'])
    else:
        complete = True
        df = pd.read_csv(a.csv, parse_dates=['ds'])
    ref = forecast_many(df, periods=meta['horizon'], freq=meta['freq'], seed=a.seed, include_history=False,
                        columns=COLUMNS, n_jobs=available_cpus())
    parts, rows = [], 0
    for f in files:  # only as many parts as the reference covers
        if rows >= len(ref):
            break
        parts.append(pd.read_csv(f, parse_dates=['ds']))
        rows += len(parts[-1])
    parts = pd.concat(parts, ignore_index=True).iloc[:len(ref)]
    ok = complete and len(parts) == len(ref)
    ok &= bool((parts['unique_id'].astype(str).to_numpy() == ref['unique_id'].astype(str).to_numpy()).all())
    ok &= bool((parts['ds'].to_numpy() == ref['ds'].to_numpy()).all())
    worst = max(float(np.max(np.abs(parts[c].to_numpy() - ref[c].to_numpy()) / np.maximum(1, np.abs(ref[c].to_numpy()))))
                for c in COLUMNS[1:])
    ok &= worst < 1e-12
    print(f'{len(parts):,} rows, {parts["unique_id"].nunique():,} series: ids and dates equal; largest relative '
          f'difference in yhat / bounds {worst:.1e} → {"OK" if ok else "MISMATCH"}')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
