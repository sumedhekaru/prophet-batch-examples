"""Six public forecasting datasets: download (pinned SHA-256) and load as train/test splits.

    uv run python -m public_datasets.pipeline.data                    # download all into data/
    uv run python -m public_datasets.pipeline.data m4 tourism         # some sources

| dataset          | series | frequency | held out | MASE season | source                                        |
|------------------|-------:|-----------|---------:|------------:|-----------------------------------------------|
| m5_item          |  3,049 | daily     |  28 days |           7 | Walmart M5 (Nixtla's m5.zip), items summed over the 10 stores |
| m5_item_store    | 30,490 | daily     |  28 days |           7 | the same file, item × store                   |
| m4_daily         |  4,227 | daily     |  14 days |           1 | M4 competition (github.com/Mcompetitions/M4-methods), official split |
| m4_weekly        |    359 | weekly    | 13 weeks |           1 | same                                          |
| m4_hourly        |    414 | hourly    | 48 hours |          24 | same                                          |
| tourism_monthly  |    366 | monthly   | 24 months|          12 | Monash forecasting archive (zenodo.org/records/4656096) |

Splits and dates follow each dataset's own convention (the same as the parallel-prophet D3 benchmark): M5's last 28
days; M4's train and test files, dates from M4-info.csv StartingDate (dd-mm-yy hh:mm; two-digit years 00-68 → 20xx)
in regular steps, so some M4 series run past 2018 (as published; no holidays, so it does not matter); Tourism from the
.tsf start timestamps, month starts. A file with a wrong checksum is never used.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / 'data'

_M4_URL = 'https://raw.githubusercontent.com/Mcompetitions/M4-methods/master/Dataset'
# source -> (url, path under data/, sha256)
FILES = {
    'm4': [
        (f'{_M4_URL}/Train/Daily-train.csv', 'm4/Daily-train.csv',
         '78e94591c60c06309f1e544fd7b2ccba28f3616b01913dd336a1d1d98483a1ec'),
        (f'{_M4_URL}/Test/Daily-test.csv', 'm4/Daily-test.csv',
         '633b0815626ae266d36872c4d53e95eb93ee8d43e79587fceec519eba3e6b05e'),
        (f'{_M4_URL}/Train/Weekly-train.csv', 'm4/Weekly-train.csv',
         'd478d3f6ed673e6ed3c2cb0fbed5425f72eedd51318ebebeb0b5ecfcefc37714'),
        (f'{_M4_URL}/Test/Weekly-test.csv', 'm4/Weekly-test.csv',
         '3b2bc4be8e636e802260dcd843ca3c5da40536a1fbe1ecb3229a97dae4f44688'),
        (f'{_M4_URL}/Train/Hourly-train.csv', 'm4/Hourly-train.csv',
         'ea59b7783573c49077a835ab6465c7d66f1474783360f310988a9a737fbca62f'),
        (f'{_M4_URL}/Test/Hourly-test.csv', 'm4/Hourly-test.csv',
         '71a57fccb15e534d973626ada4fb87febf789e9317715b7cc6dd3b5f90db6f42'),
        (f'{_M4_URL}/M4-info.csv', 'm4/M4-info.csv',
         '26a75cc9b9f65e351b39b0bdbb7e3464ac837df0baf541ab55abdd2ba1a14c88'),
    ],
    'tourism': [
        ('https://zenodo.org/records/4656096/files/tourism_monthly_dataset.zip?download=1',
         'tourism/tourism_monthly_dataset.zip',
         '6e434ad8a0ef6acb55ebee0e1d1ffe22707ea4e62c05e091326267f3a5b4a93c'),
    ],
    'm5': [
        ('https://github.com/Nixtla/m5-forecasts/raw/main/datasets/m5.zip', 'm5/m5.zip',
         'cc704ba15d6802f8262e6ec7d4c6041e4ad6366a94365e8c84f721e450eed774'),
    ],
}
SOURCE = {'m5_item': 'm5', 'm5_item_store': 'm5', 'm4_daily': 'm4', 'm4_weekly': 'm4', 'm4_hourly': 'm4',
          'tourism_monthly': 'tourism'}
NAMES = list(SOURCE)
_M5_MEMBERS = ['sales_train_evaluation.csv', 'calendar.csv']
_M4 = {'daily': ('Daily', 'D', 14, 1), 'weekly': ('Weekly', '7D', 13, 1), 'hourly': ('Hourly', 'h', 48, 24)}


@dataclass
class Dataset:
    """train: long frame (unique_id, ds, y); train_wide / test_wide: one row per series (values in time order, NaN
    padded at the end where series differ in length), for the metrics."""

    name: str
    freq: str
    horizon: int
    season: int
    train: pd.DataFrame
    train_wide: pd.DataFrame
    test_wide: pd.DataFrame


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def _fetch(url: str, path: Path, expected: str) -> str:
    if path.exists():
        if sha256(path) == expected:
            return 'ok'
        print(f'  {path.name}: checksum mismatch, downloading again')
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.part')
    with urllib.request.urlopen(url) as r, open(tmp, 'wb') as f:
        while block := r.read(1 << 20):
            f.write(block)
    got = sha256(tmp)
    if got != expected:
        tmp.unlink()
        raise RuntimeError(f'{url}: checksum {got} != pinned {expected}')
    tmp.replace(path)
    return 'downloaded'


def fetch(sources: list[str] | None = None, data_dir: Path = DATA_DIR) -> None:
    """Download and verify the files of the given sources (default: all), extracting what the loaders read."""
    for source in sources or list(FILES):
        for url, rel, expected in FILES[source]:
            path = data_dir / rel
            action = _fetch(url, path, expected)
            if path.suffix == '.zip':
                with zipfile.ZipFile(path) as z:
                    names = _M5_MEMBERS if source == 'm5' else z.namelist()
                    missing = [n for n in names if not (path.parent / n).exists()]
                    z.extractall(path.parent, members=missing)
                action += f', extracted {len(missing)} new file(s)'
            print(f'{rel}: {action}')


def _sample(count: int, n: int | None, seed: int) -> list[int]:
    """Indices of a reproducible random sample of n of count (all, in order, when n is None)."""
    if n is None or n >= count:
        return list(range(count))
    return sorted(np.random.default_rng(seed).choice(count, size=n, replace=False))


def _dataset(name: str, freq: str, horizon: int, season: int,
             series: list[tuple[str, pd.DatetimeIndex, np.ndarray]]) -> Dataset:
    ids = [sid for sid, _, _ in series]
    lens = [len(y) - horizon for _, _, y in series]
    train = pd.DataFrame({'unique_id': np.repeat(np.array(ids, dtype=object), lens),
                          'ds': np.concatenate([ds[:-horizon].to_numpy() for _, ds, _ in series]),
                          'y': np.concatenate([y[:-horizon] for _, _, y in series])})
    train_wide = pd.DataFrame.from_dict({sid: y[:-horizon] for sid, _, y in series}, orient='index').loc[ids]
    test_wide = pd.DataFrame([y[-horizon:] for _, _, y in series], index=ids)
    return Dataset(name, freq, horizon, season, train, train_wide, test_wide)


def _m5(level: str, n: int | None, seed: int, data_dir: Path) -> Dataset:
    sales = pd.read_csv(data_dir / 'm5' / 'sales_train_evaluation.csv')
    day_cols = [c for c in sales.columns if c.startswith('d_')]
    if level == 'item':
        wide = sales.groupby('item_id')[day_cols].sum()
    else:
        wide = sales.set_index(sales['item_id'] + '_' + sales['store_id'])[day_cols]
    # Calendar rows are in day order: d_1 is the first date.
    dates = pd.to_datetime(pd.read_csv(data_dir / 'm5' / 'calendar.csv', usecols=['date'])['date'])
    ds = pd.DatetimeIndex(dates.iloc[[int(c[2:]) - 1 for c in day_cols]].to_numpy())
    values = wide.to_numpy(dtype=np.float32).astype(float)  # float32 as in D3, so the inputs match bit for bit
    series = [(str(wide.index[i]), ds, values[i]) for i in _sample(len(wide), n, seed)]
    return _dataset(f'm5_{level}', 'D', 28, 7, series)


def _read_m4(path: Path) -> dict[str, np.ndarray]:
    with open(path, newline='') as f:
        rows = csv.reader(f)
        next(rows)
        return {r[0]: np.array([float(v) for v in r[1:] if v]) for r in rows}


def _m4(which: str, n: int | None, seed: int, data_dir: Path) -> Dataset:
    stem, freq, horizon, season = _M4[which]
    train = _read_m4(data_dir / 'm4' / f'{stem}-train.csv')
    test = _read_m4(data_dir / 'm4' / f'{stem}-test.csv')
    info = pd.read_csv(data_dir / 'm4' / 'M4-info.csv', index_col='M4id')
    ids = list(train)
    series = []
    for i in _sample(len(ids), n, seed):
        sid = ids[i]
        assert len(test[sid]) == horizon, sid
        y = np.concatenate([train[sid], test[sid]])
        start = pd.to_datetime(info.at[sid, 'StartingDate'], format='%d-%m-%y %H:%M')
        series.append((sid, pd.date_range(start, periods=len(y), freq=freq), y))
    return _dataset(f'm4_{which}', freq, horizon, season, series)


def _tourism_monthly(n: int | None, seed: int, data_dir: Path) -> Dataset:
    text = (data_dir / 'tourism' / 'tourism_monthly_dataset.tsf').read_text(encoding='latin-1')
    lines = text.splitlines()
    horizon = int(next(ln.split()[1] for ln in lines if ln.startswith('@horizon')))
    rows = [ln for ln in lines[lines.index('@data') + 1:] if ln.strip()]
    series = []
    for i in _sample(len(rows), n, seed):
        sid, start, values = rows[i].split(':')
        y = np.array([float(v) for v in values.split(',')])
        start_ts = pd.to_datetime(start, format='%Y-%m-%d %H-%M-%S')
        series.append((sid, pd.date_range(start_ts, periods=len(y), freq='MS'), y))
    return _dataset('tourism_monthly', 'MS', horizon, 12, series)


def load(name: str, n: int | None = None, seed: int = 0, data_dir: Path = DATA_DIR) -> Dataset:
    """A dataset (all series, or a reproducible random sample of n), as D3 loads it."""
    if name in ('m5_item', 'm5_item_store'):
        return _m5(name[3:], n, seed, data_dir)
    if name.startswith('m4_'):
        return _m4(name[3:], n, seed, data_dir)
    if name == 'tourism_monthly':
        return _tourism_monthly(n, seed, data_dir)
    raise ValueError(f'unknown dataset {name!r}; choose from {NAMES}')


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('sources', nargs='*', help=f"sources (default: all of {', '.join(FILES)}) or dataset names")
    p.add_argument('--data-dir', type=Path, default=DATA_DIR)
    a = p.parse_args()
    sources = sorted({SOURCE.get(s, s) for s in a.sources})
    unknown = [s for s in sources if s not in FILES]
    if unknown:
        p.error(f"unknown source(s): {', '.join(unknown)}")
    fetch(sources or None, a.data_dir)
    return 0


if __name__ == '__main__':
    sys.exit(main())
