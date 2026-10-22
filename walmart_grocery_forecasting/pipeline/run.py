"""Run the use case: stock Prophet vs prophet-batch on M5 FOODS items, 28-day holdout; accuracy and speed.

    uv run python -m walmart_grocery_forecasting.pipeline.run                 # all 1,437 items
    uv run python -m walmart_grocery_forecasting.pipeline.run --n 50          # smoke run on a random sample
    uv run python -m walmart_grocery_forecasting.pipeline.run --model events_snap   # holidays + SNAP (models.py)

Writes results/runs/<env>-<model>-<n>-<timestamp>.{json,npz,md} (JSON: everything incl. per-series metrics; npz: the test-day
forecasts of every method; md: the summary tables). Needs the data: python -m walmart_grocery_forecasting.pipeline.data
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from examples_core.forecast import Result, run_batch, run_forecast_many, run_stock_pool, run_stock_serial
from examples_core.records import (MemoryRecorder, aligned, available_cpus, evaluate, machine_info, paired,
                                   prophet_batch_label, utf8_stdout)

from . import data
from .models import VARIANTS, ModelSpec

HERE = Path(__file__).resolve().parents[1]
RUNS = HERE / 'results' / 'runs'
SEASON = 7  # MASE seasonal period for daily retail data


def markdown(info: dict[str, Any], n: int, rows: list[dict[str, Any]], checks: dict[str, Any]) -> str:
    v = info['versions']
    lines = [f"# walmart_grocery_forecasting: {n:,} M5 FOODS items, 28-day holdout", '',
             f"{info['timestamp']} · {info['cpu']} ({info['logical_cpus']} logical CPUs) · {info['platform']} · "
             f"Python {info['python']} · prophet {v['prophet']} · prophet-batch {prophet_batch_label(info)} "
             f"· examples {info['commits']['prophet-batch-examples']}", '',
             f"Model: `{info['model']}` (see pipeline/models.py)", '',
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
    utf8_stdout()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--n', type=int, default=None, help='random sample of n items (default: all)')
    p.add_argument('--serial-n', type=int, default=30, help='items timed for stock_serial (default 30)')
    p.add_argument('--workers', type=int, default=available_cpus(),
                   help='process count (default: the CPUs available to this process)')
    p.add_argument('--model', choices=VARIANTS, default='default', help='model variant (default: Prophet())')
    p.add_argument('--env', default='local', help='environment label for the output files')
    p.add_argument('--data-dir', type=Path, default=data.DATA_DIR)
    p.add_argument('--out', type=Path, default=RUNS, help=f'output directory (default {RUNS})')
    a = p.parse_args()

    train, test = data.split(data.load_items(a.data_dir))
    if a.n is not None and a.n < len(train):
        rng = np.random.default_rng(0)
        keep = np.sort(rng.choice(len(train), size=a.n, replace=False))
        train, test = train.iloc[keep], test.iloc[keep]
    n, h, ids = len(train), test.shape[1], list(train.index)
    spec = ModelSpec(a.model, a.data_dir)
    long_df = spec.with_regressors(data.to_long(train))
    series = {sid: g.drop(columns='unique_id').reset_index(drop=True) for sid, g in long_df.groupby('unique_id', sort=False)}
    serial_ids = list(np.random.default_rng(1).choice(ids, size=min(a.serial_n, n), replace=False))
    print(f'{n:,} items, train {train.shape[1]:,} days, test {h}; model {a.model}; workers {a.workers}')

    results: list[Result] = []
    steps = [('stock_serial', lambda: [run_stock_serial({s: series[s] for s in serial_ids}, h, spec)]),
             ('stock_pool', lambda: [run_stock_pool(series, h, spec, a.workers)]),
             ('batch n_jobs=1', lambda: run_batch(long_df, h, spec, 1)),
             (f'batch n_jobs={a.workers}', lambda: run_batch(long_df, h, spec, a.workers)),
             (f'forecast_many n_jobs={a.workers}', lambda: run_forecast_many(long_df, h, spec, a.workers))]
    memory = MemoryRecorder()
    for label, step in steps:
        print(f'{label} ...', flush=True)
        memory.step(label)
        for r in step():
            results.append(r)
            print(f'  {r.method:15s} workers {r.workers:2d}: fit {r.fit_s:7.1f} s  forecast {r.predict_s:7.1f} s'
                  f'  ({r.timed_n} series)', flush=True)

    memory_record = memory.stop()
    for label, m in memory_record['steps'].items():
        workers = (f", largest worker {m['worker_peak_gb']:.2f} GB, all workers {m['workers_total_peak_gb']:.2f} GB"
                   if m['worker_peak_gb'] is not None else '')
        print(f"  memory {label}: peak {m['parent_peak_gb']:.2f} GB here{workers}", flush=True)
    stock = next(r for r in results if r.method == 'stock_pool')
    stock_acc = evaluate(stock, train, test, SEASON)
    rows, per_series = [], {}
    for r in results:
        row: dict[str, Any] = {'method': r.method, 'workers': r.workers, 'timed_n': r.timed_n,
                               'fit_s': r.fit_s * n / r.timed_n, 'predict_s': r.predict_s * n / r.timed_n,
                               'total_s': r.seconds_for(n)}
        if r.timed_n == n and (r.method == 'stock_pool' or r.workers == a.workers):
            acc = evaluate(r, train, test, SEASON)
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
    checks['series fit by Stan (fallbacks)'] = f'{len(fallbacks)}' + (f': {fallbacks}' if fallbacks else '')

    info = {**machine_info(), 'model': a.model}
    a.out.mkdir(parents=True, exist_ok=True)
    stem = a.out / f"{a.env}-{a.model}-{n}-{datetime.now():%Y%m%d-%H%M%S}"
    stem.with_suffix('.json').write_text(json.dumps(
        {'machine': info, 'args': {k: str(v) for k, v in vars(a).items()}, 'n': n, 'horizon': h, 'ids': ids,
         'rows': rows, 'checks': checks, 'per_series': per_series, 'memory': memory_record}, indent=1, default=str), encoding='utf-8')
    np.savez_compressed(stem.with_suffix('.npz'), ids=np.array(ids), test_ds=test.columns.to_numpy(),
                        **{f'{r.method}_{r.workers}_{k}': aligned(r, ids, k) for r in results if r.timed_n == n
                           for k in ('yhat', 'lower', 'upper', 'lp')})
    md = markdown(info, n, rows, checks)
    stem.with_suffix('.md').write_text(md, encoding='utf-8')
    print('\n' + md + f'\nsaved {stem}.{{json,npz,md}}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
