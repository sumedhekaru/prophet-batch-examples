"""Run the use case: stock Prophet vs prophet-batch on M5 FOODS items, 28-day holdout; accuracy and speed.

    uv run python -m walmart_grocery_forecasting.pipeline.run                 # all 1,437 items
    uv run python -m walmart_grocery_forecasting.pipeline.run --n 50          # smoke run on a random sample

Writes results/runs/<env>-<n>-<timestamp>.{json,npz,md} (JSON: everything incl. per-series metrics; npz: the test-day
forecasts of every method; md: the summary tables). Needs the data: python -m walmart_grocery_forecasting.pipeline.data
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import data
from .forecast import Result, run_batch, run_stock_pool, run_stock_serial
from .metrics import coverage, mase, smape, wape_parts

HERE = Path(__file__).resolve().parents[1]
RUNS = HERE / 'results' / 'runs'
SEASON = 7  # MASE seasonal period for daily retail data


def _cmd(*args: str) -> str | None:
    try:
        return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def machine_info() -> dict[str, Any]:
    def commit(path: Path) -> str | None:
        rev = _cmd('git', '-C', str(path), 'rev-parse', '--short', 'HEAD')
        dirty = _cmd('git', '-C', str(path), 'status', '--porcelain', '--untracked-files=no')
        return f'{rev}{"+dirty" if dirty else ""}' if rev else None

    import prophet_batch

    return {
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'platform': platform.platform(),
        'cpu': _cmd('sysctl', '-n', 'machdep.cpu.brand_string') or platform.processor(),
        'logical_cpus': os.cpu_count(),
        'python': sys.version.split()[0],
        'versions': {p: version(p) for p in ('prophet', 'prophet-batch', 'cmdstanpy', 'numpy', 'pandas')},
        'commits': {'prophet-batch-examples': commit(HERE.parent),
                    'prophet-batch': commit(Path(prophet_batch.__file__).resolve().parents[2])},
        'thread_env': {v: os.environ.get(v) for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                                                      'VECLIB_MAXIMUM_THREADS')},
    }


def evaluate(r: Result, train: pd.DataFrame, test: pd.DataFrame) -> dict[str, Any]:
    """Per-series metrics (in train's item order) and their summary."""
    pos = {sid: i for i, sid in enumerate(r.ids)}
    err = scale = 0.0
    sm, ms, cov = [], [], []
    for sid in train.index:
        i, y = pos[sid], test.loc[sid].to_numpy()
        e, s = wape_parts(y, r.yhat[i])
        err, scale = err + e, scale + s
        sm.append(smape(y, r.yhat[i]))
        ms.append(mase(y, r.yhat[i], train.loc[sid].to_numpy(), SEASON))
        cov.append(coverage(y, r.lower[i], r.upper[i]))
    per = {'smape': np.array(sm), 'mase': np.array(ms), 'coverage': np.array(cov)}
    summary = {'wape': err / scale, 'smape': float(per['smape'].mean()), 'mase': float(np.nanmean(per['mase'])),
               'mase_median': float(np.nanmedian(per['mase'])), 'coverage': float(per['coverage'].mean())}
    return {'summary': summary, 'per_series': per}


def paired(a: np.ndarray, b: np.ndarray) -> dict[str, float]:
    """Mean of b - a over series where both are finite, with its standard error."""
    d = (b - a)[np.isfinite(b - a)]
    return {'mean': float(d.mean()), 'se': float(d.std(ddof=1) / np.sqrt(len(d))) if len(d) > 1 else 0.0}


def aligned(r: Result, ids: list[str], attr: str) -> np.ndarray:
    pos = {sid: i for i, sid in enumerate(r.ids)}
    return getattr(r, attr)[[pos[s] for s in ids]]


def markdown(info: dict[str, Any], n: int, rows: list[dict[str, Any]], checks: dict[str, Any]) -> str:
    v = info['versions']
    lines = [f"# walmart_grocery_forecasting: {n:,} M5 FOODS items, 28-day holdout", '',
             f"{info['timestamp']} · {info['cpu']} ({info['logical_cpus']} logical CPUs) · {info['platform']} · "
             f"Python {info['python']} · prophet {v['prophet']} · prophet-batch {v['prophet-batch']} "
             f"({info['commits']['prophet-batch']}) · examples {info['commits']['prophet-batch-examples']}", '',
             '## Speed (fit + forecast of history and 28 days)', '',
             '| method | workers | fit s | forecast s | total s | vs stock pool |', '|---|---:|---:|---:|---:|---:|']
    pool = next(r['total_s'] for r in rows if r['method'] == 'stock_pool')
    for r in rows:
        note = f" (timed on {r['timed_n']}, extrapolated)" if r['timed_n'] < n else ''
        lines.append(f"| {r['method']}{note} | {r['workers']} | {r['fit_s']:.1f} | {r['predict_s']:.1f} | "
                     f"{r['total_s']:.1f} | {pool / r['total_s']:.1f}× |")
    lines += ['', '## Accuracy on the 28 held-out days', '',
              '| method | WAPE | sMAPE | MASE mean | MASE median | 80% coverage | Δ MASE vs stock (± 2 SE) |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        if 'accuracy' not in r:
            continue
        s, d = r['accuracy'], r.get('mase_vs_stock')
        delta = f"{d['mean']:+.4f} ± {2 * d['se']:.4f}" if d else '–'
        lines.append(f"| {r['method']} (n_jobs={r['workers']}) | {s['wape']:.4f} | {s['smape']:.2f} | {s['mase']:.4f} | "
                     f"{s['mase_median']:.4f} | {s['coverage']:.3f} | {delta} |")
    lines += ['', '## Checks', ''] + [f'- {k}: {v}' for k, v in checks.items()]
    return '\n'.join(lines) + '\n'


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--n', type=int, default=None, help='random sample of n items (default: all)')
    p.add_argument('--serial-n', type=int, default=30, help='items timed for stock_serial (default 30)')
    p.add_argument('--workers', type=int, default=os.cpu_count(), help='process count (default: all CPUs)')
    p.add_argument('--env', default='local', help='environment label for the output files')
    p.add_argument('--data-dir', type=Path, default=data.DATA_DIR)
    a = p.parse_args()

    train, test = data.split(data.load_items(a.data_dir))
    if a.n is not None and a.n < len(train):
        rng = np.random.default_rng(0)
        keep = np.sort(rng.choice(len(train), size=a.n, replace=False))
        train, test = train.iloc[keep], test.iloc[keep]
    n, h, ids = len(train), test.shape[1], list(train.index)
    long_df = data.to_long(train)
    series = {sid: g[['ds', 'y']].reset_index(drop=True) for sid, g in long_df.groupby('unique_id', sort=False)}
    serial_ids = list(np.random.default_rng(1).choice(ids, size=min(a.serial_n, n), replace=False))
    print(f'{n:,} items, train {train.shape[1]:,} days, test {h}; workers {a.workers}')

    results: list[Result] = []
    steps = [('stock_serial', lambda: [run_stock_serial({s: series[s] for s in serial_ids}, h)]),
             ('stock_pool', lambda: [run_stock_pool(series, h, a.workers)]),
             ('batch n_jobs=1', lambda: run_batch(long_df, h, 1)),
             (f'batch n_jobs={a.workers}', lambda: run_batch(long_df, h, a.workers))]
    for label, step in steps:
        print(f'{label} ...', flush=True)
        for r in step():
            results.append(r)
            print(f'  {r.method:15s} workers {r.workers:2d}: fit {r.fit_s:7.1f} s  forecast {r.predict_s:7.1f} s'
                  f'  ({r.timed_n} series)', flush=True)

    stock = next(r for r in results if r.method == 'stock_pool')
    stock_acc = evaluate(stock, train, test)
    rows, per_series = [], {}
    for r in results:
        row: dict[str, Any] = {'method': r.method, 'workers': r.workers, 'timed_n': r.timed_n,
                               'fit_s': r.fit_s * n / r.timed_n, 'predict_s': r.predict_s * n / r.timed_n,
                               'total_s': r.seconds_for(n)}
        if r.timed_n == n and (r.method == 'stock_pool' or r.workers == a.workers):
            acc = evaluate(r, train, test)
            row['accuracy'] = acc['summary']
            per_series[f'{r.method}_{r.workers}'] = {k: v.tolist() for k, v in acc['per_series'].items()}
            if r is not stock:
                row['mase_vs_stock'] = paired(stock_acc['per_series']['mase'], acc['per_series']['mase'])
        rows.append(row)

    batch = {(r.method, r.workers): r for r in results if r.method.startswith('batch')}
    checks: dict[str, Any] = {}
    for mode in ('batch_sampled', 'batch_analytic'):
        one, many = batch[(mode, 1)], batch[(mode, a.workers)]
        same = all(np.array_equal(aligned(one, ids, k), aligned(many, ids, k)) for k in ('yhat', 'lower', 'upper'))
        checks[f'{mode}: n_jobs=1 and n_jobs={a.workers} forecasts bit-identical'] = same
    gain = aligned(batch[('batch_sampled', a.workers)], ids, 'lp') - aligned(stock, ids, 'lp')
    checks['log posterior ≥ Stan\'s (share of series, tol 1e-6)'] = f'{np.mean(gain >= -1e-6):.4f}'
    checks['log posterior gain over Stan (min / median)'] = f'{gain.min():.3g} / {np.median(gain):.3g}'
    fallbacks = batch[('batch_sampled', 1)].extra.get('fallbacks', {})
    checks['series fit by Stan (fallbacks)'] = f'{len(fallbacks)}' + (f': {fallbacks}' if fallbacks else '')

    info = machine_info()
    RUNS.mkdir(parents=True, exist_ok=True)
    stem = RUNS / f"{a.env}-{n}-{datetime.now():%Y%m%d-%H%M%S}"
    stem.with_suffix('.json').write_text(json.dumps(
        {'machine': info, 'args': {k: str(v) for k, v in vars(a).items()}, 'n': n, 'horizon': h, 'ids': ids,
         'rows': rows, 'checks': checks, 'per_series': per_series}, indent=1, default=str))
    np.savez_compressed(stem.with_suffix('.npz'), ids=np.array(ids), test_ds=test.columns.to_numpy(),
                        **{f'{r.method}_{r.workers}_{k}': aligned(r, ids, k) for r in results if r.timed_n == n
                           for k in ('yhat', 'lower', 'upper')})
    md = markdown(info, n, rows, checks)
    stem.with_suffix('.md').write_text(md)
    print('\n' + md + f'\nsaved {stem}.{{json,npz,md}}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
