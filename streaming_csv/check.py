"""Check a streaming run: its parts together equal one in-memory forecast_many of the whole CSV.

    uv run python -m streaming_csv.check data/streaming/m5_item-x1.csv     # reads data/streaming/m5_item-x1-out/

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

from examples_core.records import available_cpus

from .run import COLUMNS


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('csv', type=Path)
    p.add_argument('--out', type=Path, default=None)
    p.add_argument('--seed', type=int, default=0)
    a = p.parse_args()
    from prophet_batch import forecast_many

    meta = json.loads(a.csv.with_suffix('.json').read_text())
    out_dir = a.out or a.csv.with_name(a.csv.stem + '-out')
    df = pd.read_csv(a.csv, parse_dates=['ds'])
    ref = forecast_many(df, periods=meta['horizon'], freq=meta['freq'], seed=a.seed, include_history=False,
                        columns=COLUMNS, n_jobs=available_cpus())
    parts = pd.concat([pd.read_csv(f, parse_dates=['ds']) for f in sorted(out_dir.glob('part-*.csv'))],
                      ignore_index=True)
    ok = len(parts) == len(ref)
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
