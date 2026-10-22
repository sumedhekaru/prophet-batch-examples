"""Write the processed input CSV for the streaming example: one row per (series, day), sorted by series id.

    uv run python -m streaming_csv.prepare                            # M5 items (3,049 series), 1 copy
    uv run python -m streaming_csv.prepare --dataset m5_item_store    # 30,490 series
    uv run python -m streaming_csv.prepare --copies 4                 # 4 × the series (ids suffixed _c2 .. _c4)
    uv run python -m streaming_csv.prepare --copies 328 --perturb --gzip --jobs 8   # ≈ 1 million different series

This stands for whatever a real pipeline produces upstream (an export, a nightly job): the file is prepared once,
sorted by series id, and every series has the same number of rows, which is written next to it
(<name>.json: rows_per_series, series). Knowing that, the reader can take whole series per chunk without looking
for boundaries. Copies are the same series under new ids, to make larger files for the memory check; with
--perturb, every copy after the first is resampled (y' = Poisson(f·y), f ~ U(0.5, 2) per series and copy, seeded),
so the copies are different series of the same kind, not repeats. --gzip writes <name>.csv.gz (gzip members written
by --jobs processes, concatenated in order: one valid gzip file).
"""

from __future__ import annotations

import argparse
import gzip
import json
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from public_datasets.pipeline import data

OUT_DIR = Path(__file__).resolve().parents[1] / 'data' / 'streaming'


def _copy(train: pd.DataFrame, order: np.ndarray, rows: int, c: int, perturb: bool) -> pd.DataFrame:
    """Copy c (1-based) of the series, in id order: the originals for c = 1, ids suffixed _c<c> after."""
    part = train.copy()
    if c > 1:
        part['unique_id'] = part['unique_id'] + f'_c{c}'
        if perturb:
            rng = np.random.default_rng(c)
            f = np.repeat(rng.uniform(0.5, 2.0, size=len(part) // rows), rows)
            part['y'] = rng.poisson(f * part['y'].to_numpy()).astype(float)
    # sorted by series id within the copy; copies come one after another (their ids sort after the originals'
    # within each copy block, which is all the reader needs: each series' rows are contiguous)
    return pd.concat([part.iloc[i * rows:(i + 1) * rows] for i in order])


_SHARED: tuple = ()


def _init(*shared: object) -> None:
    global _SHARED
    _SHARED = shared  # train, order, rows, perturb: sent once per process, not once per copy


def _write_part(c: int, path: Path) -> Path:
    train, order, rows, perturb = _SHARED
    with gzip.open(path, 'wt', compresslevel=1, encoding='utf-8', newline='') as f:
        _copy(train, order, rows, c, perturb).to_csv(f, index=False, header=(c == 1), date_format='%Y-%m-%d')
    return path


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--dataset', choices=['m5_item', 'm5_item_store'], default='m5_item')
    p.add_argument('--copies', type=int, default=1)
    p.add_argument('--perturb', action='store_true', help='resample every copy after the first (different series)')
    p.add_argument('--gzip', action='store_true', help='write <name>.csv.gz')
    p.add_argument('--jobs', type=int, default=1, help='processes writing gzip members (with --gzip)')
    p.add_argument('--out-dir', type=Path, default=OUT_DIR)
    a = p.parse_args()
    data.fetch(['m5'])
    ds = data.load(a.dataset)
    train = ds.train  # unique_id, ds, y: the training days of every series (the forecast horizon is held out)
    ids = list(ds.train_wide.index)
    rows = int(train.groupby('unique_id', sort=False).size().iloc[0])
    assert (train.groupby('unique_id', sort=False).size() == rows).all(), 'series of different lengths'
    name = f"{a.dataset}-x{a.copies}{'p' if a.perturb else ''}"
    a.out_dir.mkdir(parents=True, exist_ok=True)
    order = np.argsort(np.array(ids, dtype=object), kind='stable')
    if a.gzip:
        path = a.out_dir / f'{name}.csv.gz'
        tmp = a.out_dir / f'{name}-parts'
        tmp.mkdir(exist_ok=True)
        copies = range(1, a.copies + 1)
        with ProcessPoolExecutor(max_workers=a.jobs, initializer=_init, initargs=(train, order, rows, a.perturb)) \
                as pool, open(path, 'wb') as out:
            for part in pool.map(_write_part, copies, [tmp / f'{c:05d}.gz' for c in copies]):  # in order: members concatenated as they finish
                with open(part, 'rb') as f:
                    shutil.copyfileobj(f, out, 1 << 24)
                part.unlink()
        tmp.rmdir()
    else:
        path = a.out_dir / f'{name}.csv'
        with open(path, 'w', encoding='utf-8') as f:
            for c in range(1, a.copies + 1):
                _copy(train, order, rows, c, a.perturb).to_csv(f, index=False, header=(c == 1),
                                                               date_format='%Y-%m-%d')
    meta = {'rows_per_series': rows, 'series': len(ids) * a.copies, 'horizon': ds.horizon, 'freq': ds.freq,
            'source': a.dataset, 'copies': a.copies, 'perturbed': a.perturb}
    meta_path(path).write_text(json.dumps(meta, indent=1))
    print(f'wrote {path} ({path.stat().st_size / 1e6:,.0f} MB): {meta}')
    return 0


def base_name(path: Path) -> str:
    """The file's name without .csv / .csv.gz."""
    return path.name.removesuffix('.gz').removesuffix('.csv')


def meta_path(path: Path) -> Path:
    """<name>.json next to <name>.csv or <name>.csv.gz."""
    return path.with_name(base_name(path) + '.json')


if __name__ == '__main__':
    sys.exit(main())
