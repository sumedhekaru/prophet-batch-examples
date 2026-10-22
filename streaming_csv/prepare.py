"""Write the processed input CSV for the streaming example: one row per (series, day), sorted by series id.

    uv run python -m streaming_csv.prepare                            # M5 items (3,049 series), 1 copy
    uv run python -m streaming_csv.prepare --dataset m5_item_store    # 30,490 series
    uv run python -m streaming_csv.prepare --copies 4                 # 4 × the series (ids suffixed _c2 .. _c4)

This stands for whatever a real pipeline produces upstream (an export, a nightly job): the file is prepared once,
sorted by series id, and every series has the same number of rows, which is written next to it
(<name>.json: rows_per_series, series). Knowing that, the reader can take whole series per chunk without looking
for boundaries. Copies are the same series under new ids, to make larger files for the memory check.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from public_datasets.pipeline import data

OUT_DIR = Path(__file__).resolve().parents[1] / 'data' / 'streaming'


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--dataset', choices=['m5_item', 'm5_item_store'], default='m5_item')
    p.add_argument('--copies', type=int, default=1)
    p.add_argument('--out-dir', type=Path, default=OUT_DIR)
    a = p.parse_args()
    data.fetch(['m5'])
    ds = data.load(a.dataset)
    train = ds.train  # unique_id, ds, y: the training days of every series (the forecast horizon is held out)
    ids = list(ds.train_wide.index)
    rows = int(train.groupby('unique_id', sort=False).size().iloc[0])
    assert (train.groupby('unique_id', sort=False).size() == rows).all(), 'series of different lengths'
    name = f'{a.dataset}-x{a.copies}'
    a.out_dir.mkdir(parents=True, exist_ok=True)
    path = a.out_dir / f'{name}.csv'
    order = np.argsort(np.array(ids, dtype=object), kind='stable')
    with open(path, 'w', encoding='utf-8') as f:
        for c in range(1, a.copies + 1):
            suffix = '' if c == 1 else f'_c{c}'
            part = train.copy()
            part['unique_id'] = part['unique_id'] + suffix
            # sorted by series id within the copy; copies come one after another (their ids sort after the
            # originals' within each copy block, which is all the reader needs: each series' rows are contiguous)
            blocks = [part.iloc[i * rows:(i + 1) * rows] for i in order]
            pd.concat(blocks).to_csv(f, index=False, header=(c == 1), date_format='%Y-%m-%d')
    meta = {'rows_per_series': rows, 'series': len(ids) * a.copies, 'horizon': ds.horizon, 'freq': ds.freq,
            'source': a.dataset, 'copies': a.copies}
    (a.out_dir / f'{name}.json').write_text(json.dumps(meta, indent=1))
    print(f'wrote {path} ({path.stat().st_size / 1e6:,.0f} MB): {meta}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
