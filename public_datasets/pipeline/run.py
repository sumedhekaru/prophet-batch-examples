"""Run one public dataset: stock Prophet vs prophet-batch, default Prophet(); accuracy, fit quality and speed.

    uv run python -m public_datasets.pipeline.run --dataset m4_daily            # all 4,227 series
    uv run python -m public_datasets.pipeline.run --dataset m4_daily --n 50     # smoke run on a random sample

Methods (examples_core/forecast.py): stock serial (timed on --serial-n series, extrapolated), stock pool (all series,
--workers processes), prophet-batch with n_jobs=--workers (all series; default history intervals, and
analytic), and prophet-batch with n_jobs=1 on --check-n series (timed and extrapolated; its forecasts must equal the
n_jobs=--workers ones bit for bit: a series' fit and forecast do not depend on its batch mates).
Writes results/runs/<env>-<dataset>-<n>-<timestamp>.{json,npz,md}; needs the data: python -m public_datasets.pipeline.data
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from prophet import Prophet

from examples_core.forecast import Result, run_batch, run_forecast_many, run_stock_pool, run_stock_serial
from examples_core.records import (MemoryRecorder, aligned, available_cpus, evaluate, machine_info, paired,
                                   prophet_batch_label, utf8_stdout)

from . import data

HERE = Path(__file__).resolve().parents[1]
RUNS = HERE / 'results' / 'runs'
BIG = 5000  # above this many series, the n_jobs=1 check runs on a sample (--check-n)


class DefaultSpec:
    """Default Prophet() for every series, at the dataset's frequency (examples_core.forecast.ModelSpec)."""

    regressors: list[str] = []

    def __init__(self, freq: str) -> None:
        self.freq = freq

    def kwargs(self) -> dict:
        return {}

    def __call__(self, series_id: object = None) -> Prophet:
        return Prophet()

    def with_regressors(self, df: pd.DataFrame) -> pd.DataFrame:
        return df


def markdown(info: dict[str, Any], ds: data.Dataset, rows: list[dict[str, Any]], checks: dict[str, Any]) -> str:
    v, n = info['versions'], len(ds.train_wide)
    lines = [f'# public_datasets: {ds.name}, {n:,} series, {ds.horizon}-step holdout ({ds.freq})', '',
             f"{info['timestamp']} · {info['cpu']} ({info['logical_cpus']} logical CPUs) · {info['platform']} · "
             f"Python {info['python']} · prophet {v['prophet']} · prophet-batch {prophet_batch_label(info)} "
             f"· examples {info['commits']['prophet-batch-examples']}", '',
             '## Speed (fit + forecast of history and the holdout)', '',
             '| method | workers | fit s | forecast s | total s | vs stock pool |', '|---|---:|---:|---:|---:|---:|']
    pool = next(r['total_s'] for r in rows if r['method'] == 'stock_pool')
    for r in rows:
        note = f" (timed on {r['timed_n']:,}, extrapolated)" if r['timed_n'] < n else ''
        lines.append(f"| {r['method']}{note} | {r['workers']} | {r['fit_s']:.1f} | {r['predict_s']:.1f} | "
                     f"{r['total_s']:.1f} | {pool / r['total_s']:.1f}× |")
    lines += ['', '## Accuracy on the held-out steps', '',
              '| method | WAPE | sMAPE | MASE mean | MASE median | 80% coverage | Δ MASE vs stock (± 2 SE) |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        if 'accuracy' not in r:
            continue
        s, d = r['accuracy'], r.get('mase_vs_stock')
        delta = f"{d['mean']:+.4f} ± {2 * d['se']:.4f}" if d else '–'
        lines.append(f"| {r['method']} (n_jobs={r['workers']}) | {s['wape']:.4f} | {s['smape']:.2f} | "
                     f"{s['mase']:.4f} | {s['mase_median']:.4f} | {s['coverage']:.3f} | {delta} |")
    lines += ['', '## Checks', ''] + [f'- {k}: {v}' for k, v in checks.items()]
    return '\n'.join(lines) + '\n'


def main() -> int:
    utf8_stdout()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--dataset', choices=data.NAMES, required=True)
    p.add_argument('--n', type=int, default=None, help='random sample of n series (default: all)')
    p.add_argument('--serial-n', type=int, default=30, help='series timed for stock_serial (default 30)')
    p.add_argument('--check-n', type=int, default=2000,
                   help=f'series for the prophet-batch n_jobs=1 run when the dataset has more than {BIG:,} (default 2000)')
    p.add_argument('--workers', type=int, default=available_cpus(),
                   help='process count (default: the CPUs available to this process)')
    p.add_argument('--env', default='local', help='environment label for the output files')
    p.add_argument('--data-dir', type=Path, default=data.DATA_DIR)
    p.add_argument('--out', type=Path, default=RUNS, help=f'output directory (default {RUNS})')
    a = p.parse_args()

    ds = data.load(a.dataset, a.n, data_dir=a.data_dir)
    ids = list(ds.train_wide.index)
    n, h, spec = len(ids), ds.horizon, DefaultSpec(ds.freq)
    series = {sid: g[['ds', 'y']].reset_index(drop=True) for sid, g in ds.train.groupby('unique_id', sort=False)}
    rng = np.random.default_rng(1)
    serial_ids = list(rng.choice(ids, size=min(a.serial_n, n), replace=False))
    check_ids = ids if n <= BIG else sorted(np.random.default_rng(2).choice(ids, size=a.check_n, replace=False))
    check_df = ds.train if len(check_ids) == n else ds.train[ds.train['unique_id'].isin(set(check_ids))]
    print(f'{ds.name}: {n:,} series, horizon {h} ({ds.freq}); workers {a.workers}; n_jobs=1 check on '
          f'{len(check_ids):,}', flush=True)

    results: list[Result] = []
    steps = [('stock_serial', lambda: [run_stock_serial({s: series[s] for s in serial_ids}, h, spec)]),
             ('stock_pool', lambda: [run_stock_pool(series, h, spec, a.workers)]),
             (f'batch n_jobs={a.workers}', lambda: run_batch(ds.train, h, spec, a.workers)),
             (f'forecast_many n_jobs={a.workers}', lambda: run_forecast_many(ds.train, h, spec, a.workers)),
             ('batch n_jobs=1', lambda: run_batch(check_df, h, spec, 1))]
    memory = MemoryRecorder()
    for label, step in steps:
        print(f'{label} ...', flush=True)
        memory.step(label)
        for r in step():
            results.append(r)
            print(f'  {r.method:15s} workers {r.workers:2d}: fit {r.fit_s:7.1f} s  forecast {r.predict_s:7.1f} s'
                  f'  ({r.timed_n:,} series)', flush=True)

    # timed_n < n for the sampled runs: their times are extrapolated to n (Result.seconds_for)
    memory_record = memory.stop()
    for label, m in memory_record['steps'].items():
        workers = (f", largest worker {m['worker_peak_gb']:.2f} GB, all workers {m['workers_total_peak_gb']:.2f} GB"
                   if m['worker_peak_gb'] is not None else '')
        print(f"  memory {label}: peak {m['parent_peak_gb']:.2f} GB here{workers}", flush=True)
    stock = next(r for r in results if r.method == 'stock_pool')
    stock_acc = evaluate(stock, ds.train_wide, ds.test_wide, ds.season)
    rows, per_series = [], {}
    for r in results:
        row: dict[str, Any] = {'method': r.method, 'workers': r.workers, 'timed_n': r.timed_n,
                               'fit_s': r.fit_s * n / r.timed_n, 'predict_s': r.predict_s * n / r.timed_n,
                               'total_s': r.seconds_for(n)}
        if r.timed_n == n and r.method != 'stock_serial' and (r.method == 'stock_pool' or r.workers == a.workers):
            acc = evaluate(r, ds.train_wide, ds.test_wide, ds.season)
            row['accuracy'] = acc['summary']
            per_series[f'{r.method}_{r.workers}'] = {k: v.tolist() for k, v in acc['per_series'].items()}
            if r is not stock:
                row['mase_vs_stock'] = paired(stock_acc['per_series']['mase'], acc['per_series']['mase'])
        rows.append(row)

    batch = {(r.method, r.workers): r for r in results if r.method.startswith('batch')}
    checks: dict[str, Any] = {}
    for mode in ('batch_sampled', 'batch_analytic'):
        one, many = batch[(mode, 1)], batch[(mode, a.workers)]
        same = all(np.array_equal(aligned(one, check_ids, k), aligned(many, check_ids, k))
                   for k in ('yhat', 'lower', 'upper', 'lp'))
        checks[f'{mode}: n_jobs=1 ({len(check_ids):,} series) and n_jobs={a.workers} bit-identical'] = same
    for mode in ('sampled', 'analytic'):
        one_step = next(r for r in results if r.method == f'forecast_many_{mode}')
        two_step = batch[(f'batch_{mode}', a.workers)]
        same = all(np.array_equal(aligned(one_step, ids, k), aligned(two_step, ids, k))
                   for k in ('yhat', 'lower', 'upper', 'lp'))
        checks[f'forecast_many_{mode} and batch_{mode} (n_jobs={a.workers}) bit-identical'] = same
    gain = aligned(batch[('batch_sampled', a.workers)], ids, 'lp') - aligned(stock, ids, 'lp')
    checks['log posterior ≥ Stan\'s (share of series, tol 1e-6)'] = f'{np.mean(gain >= -1e-6):.4f}'
    checks['log posterior gain over Stan (min / median)'] = f'{gain.min():.3g} / {np.median(gain):.3g}'
    fallbacks = batch[('batch_sampled', 1)].extra.get('fallbacks', {})
    checks['series fit by Stan (fallbacks, in the n_jobs=1 run)'] = (f'{len(fallbacks)}'
                                                                    + (f': {fallbacks}' if fallbacks else ''))

    info = {**machine_info(), 'dataset': ds.name}
    a.out.mkdir(parents=True, exist_ok=True)
    stem = a.out / f'{a.env}-{ds.name}-{n}-{datetime.now():%Y%m%d-%H%M%S}'
    stem.with_suffix('.json').write_text(json.dumps(
        {'machine': info, 'args': {k: str(v) for k, v in vars(a).items()}, 'n': n, 'horizon': h, 'ids': ids,
         'check_ids': check_ids, 'rows': rows, 'checks': checks, 'per_series': per_series, 'memory': memory_record}, indent=1, default=str),
        encoding='utf-8')
    np.savez_compressed(stem.with_suffix('.npz'), ids=np.array(ids),
                        **{f'{r.method}_{r.workers}_{k}': aligned(r, ids, k) for r in results if r.timed_n == n
                           for k in ('yhat', 'lower', 'upper', 'lp')})
    md = markdown(info, ds, rows, checks)
    stem.with_suffix('.md').write_text(md, encoding='utf-8')
    print('\n' + md + f'\nsaved {stem}.{{json,npz,md}}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
