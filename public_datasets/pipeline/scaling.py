"""Scaling curves: fit + forecast time vs number of series, and vs worker count, stock Prophet vs prophet-batch.

    uv run python -m public_datasets.pipeline.scaling                                   # the default curve
    uv run python -m public_datasets.pipeline.scaling --points 100,1000 --reps 1        # a quick one
    uv run python -m public_datasets.pipeline.scaling --workers-sweep 1,2,4,6,8,10 --points 1000 --reps 1

Each point is a sample of n series of one dataset (default m5_item_store, 30,490 series). Samples are nested: the first
n of one seeded permutation, so a larger point contains every smaller one. At each point, the same methods as run.py,
all doing fit + forecast of history and the holdout (default Prophet(), sampled and analytic history intervals):
stock pool (a process pool of stock Prophet fits), prophet-batch fit_many + predict_many (two steps) and
forecast_many (one step). forecast_many's forecasts must equal the two-step ones bit for bit (checked at every point).
--reps-large sets the repetitions of points above 5,000 series (default 1: the big runs of run.py time the whole
dataset three more times). --workers-sweep times every method at each worker count instead (n = --points).
Writes results/runs/scaling-<env>-<dataset>-<timestamp>.{json,md}; needs the data: python -m public_datasets.pipeline.data
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from examples_core.forecast import run_batch, run_forecast_many, run_stock_pool
from examples_core.records import MemoryRecorder, aligned, available_cpus, machine_info, prophet_batch_label, utf8_stdout

from . import data
from .run import RUNS, DefaultSpec

POINTS = '100,300,1000,3000,10000,30490'
LABELS = {'stock_pool': 'stock, process pool', 'batch_sampled': 'fit_many + predict_many, sampled',
          'batch_analytic': 'fit_many + predict_many, analytic', 'forecast_many_sampled': 'forecast_many, sampled',
          'forecast_many_analytic': 'forecast_many, analytic'}


def one_point(ds: data.Dataset, ids: list[str], workers: int, memory: MemoryRecorder, tag: str) -> dict[str, Any]:
    """Every method on these series: seconds (fit, forecast, total), and the forecast_many = two-step check."""
    h, spec = ds.horizon, DefaultSpec(ds.freq)
    keep = set(ids)
    train = ds.train[ds.train['unique_id'].isin(keep)]
    series = {sid: g[['ds', 'y']].reset_index(drop=True) for sid, g in train.groupby('unique_id', sort=False)}
    results = []
    for label, step in (('stock_pool', lambda: [run_stock_pool(series, h, spec, workers)]),
                        ('batch', lambda: run_batch(train, h, spec, workers)),
                        ('forecast_many', lambda: run_forecast_many(train, h, spec, workers))):
        memory.step(f'{tag} {label}')
        results += step()
    rows = {r.method: {'fit_s': r.fit_s, 'predict_s': r.predict_s, 'total_s': r.total_s} for r in results}
    by = {r.method: r for r in results}
    same = all(np.array_equal(aligned(by[f'forecast_many_{m}'], ids, k), aligned(by[f'batch_{m}'], ids, k))
               for m in ('sampled', 'analytic') for k in ('yhat', 'lower', 'upper', 'lp'))
    return {'n': len(ids), 'workers': workers, 'seconds': rows, 'forecast_many_equals_two_step': same}


def markdown(info: dict[str, Any], dataset: str, points: list[dict[str, Any]], sweep: bool) -> str:
    v = info['versions']
    key = 'workers' if sweep else 'n'
    lines = [f"# Scaling: {dataset}, time vs {'worker count' if sweep else 'number of series'}", '',
             f"{info['timestamp']} · {info['cpu']} ({info['logical_cpus']} logical CPUs) · {info['platform']} · "
             f"Python {info['python']} · prophet {v['prophet']} · prophet-batch {prophet_batch_label(info)} "
             f"· examples {info['commits']['prophet-batch-examples']}", '',
             'Seconds for fit + forecast (history and the holdout), median (min–max) over repetitions; speed-up vs '
             'the stock pool at the same point (median of the per-repetition ratios).', '',
             f"| {key} | reps | " + ' | '.join(LABELS.values()) + ' | forecast_many analytic vs pool |',
             '|---:|---:|' + '---:|' * (len(LABELS) + 1)]
    for x in sorted({p[key] for p in points}):
        group = [p for p in points if p[key] == x]
        cells = []
        for m in LABELS:
            t = np.array([p['seconds'][m]['total_s'] for p in group])
            cells.append(f'{np.median(t):.1f}' + (f' ({t.min():.1f}–{t.max():.1f})' if len(t) > 1 else ''))
        ratio = np.median([p['seconds']['stock_pool']['total_s'] / p['seconds']['forecast_many_analytic']['total_s']
                           for p in group])
        lines.append(f'| {x:,} | {len(group)} | ' + ' | '.join(cells) + f' | {ratio:.1f}× |')
    ok = all(p['forecast_many_equals_two_step'] for p in points)
    lines += ['', f"forecast_many equals fit_many + predict_many bit for bit at every point: {'yes' if ok else 'NO'}"]
    return '\n'.join(lines) + '\n'


def main() -> int:
    utf8_stdout()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--dataset', choices=data.NAMES, default='m5_item_store')
    p.add_argument('--points', default=POINTS, help=f'comma-separated numbers of series (default {POINTS})')
    p.add_argument('--reps', type=int, default=3, help='repetitions of each point up to 5,000 series (default 3)')
    p.add_argument('--reps-large', type=int, default=1, help='repetitions of points above 5,000 series (default 1)')
    p.add_argument('--workers', type=int, default=available_cpus())
    p.add_argument('--workers-sweep', default='', help='comma-separated worker counts (sweep mode)')
    p.add_argument('--env', default='local')
    p.add_argument('--data-dir', type=Path, default=data.DATA_DIR)
    p.add_argument('--out', type=Path, default=RUNS)
    a = p.parse_args()

    ds = data.load(a.dataset, data_dir=a.data_dir)
    order = list(np.random.default_rng(3).permutation(np.array(ds.train_wide.index, dtype=object)))
    sizes = [min(int(x), len(order)) for x in a.points.split(',')]
    sweep = [int(w) for w in a.workers_sweep.split(',') if w]
    plan = ([(n, w) for n in sizes for w in sweep] if sweep else [(n, a.workers) for n in sizes])
    print(f'{ds.name}: {len(order):,} series; points {plan}; reps {a.reps} (≤ 5,000), {a.reps_large} (above)',
          flush=True)
    memory = MemoryRecorder()
    points = []
    for rep in range(1, max(a.reps, a.reps_large) + 1):
        for n, w in plan:
            if rep > (a.reps if n <= 5000 else a.reps_large):
                continue
            pt = one_point(ds, order[:n], w, memory, f'n={n} workers={w} rep={rep}')
            pt['rep'] = rep
            points.append(pt)
            s = pt['seconds']
            print(f'  n {n:6,} workers {w:2d} rep {rep}: ' + ', '.join(f"{m} {s[m]['total_s']:.1f} s" for m in LABELS)
                  + f"; forecast_many = two-step: {pt['forecast_many_equals_two_step']}", flush=True)
    memory_record = memory.stop()
    info = {**machine_info(), 'dataset': ds.name}
    a.out.mkdir(parents=True, exist_ok=True)
    stem = a.out / f"scaling{'-workers' if sweep else ''}-{a.env}-{ds.name}-{datetime.now():%Y%m%d-%H%M%S}"
    stem.with_suffix('.json').write_text(json.dumps(
        {'machine': info, 'args': {k: str(v) for k, v in vars(a).items()}, 'points': points,
         'memory': memory_record}, indent=1, default=str), encoding='utf-8')
    md = markdown(info, ds.name, points, bool(sweep))
    stem.with_suffix('.md').write_text(md, encoding='utf-8')
    print('\n' + md + f'\nsaved {stem}.{{json,md}}')
    return 0 if all(p['forecast_many_equals_two_step'] for p in points) else 1


if __name__ == '__main__':
    sys.exit(main())
