"""Summarize repeated runs of pipeline.run (local, Docker, Cloud Run): speed as median (min–max), accuracy, checks.

    uv run python -m examples_core.bench_summary DIR > DIR/summary.md

DIR holds the <env>-<model>-<n>-<timestamp>.{json,npz} files of REPS repetitions per model variant (the run scripts
write them there when REPS is set). Speed-ups are computed within each run (against that run's stock pool), then
summarized over repetitions. Accuracy is that of the first repetition; the page says whether later ones match it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

from .records import prophet_batch_label

# Runs are grouped by dataset (public_datasets) or model variant (walmart); known groups in this order, then the rest.
ORDER = ['default', 'events', 'events_snap', 'm5_item_store', 'm4_daily', 'm5_item', 'm4_weekly', 'm4_hourly',
         'tourism_monthly']
MODEL_LABEL = {'default': 'default `Prophet()`', 'events': '+ M5 events as holidays',
               'events_snap': '+ events + SNAP regressors'}
METHOD_LABEL = {'stock_serial': 'stock, serial¹', 'stock_pool': 'stock, process pool',
                'batch_sampled': 'prophet-batch, sampled history intervals',
                'batch_analytic': 'prophet-batch, analytic history intervals'}


def _stat(xs: list[float], fmt: str = '{:,.1f}') -> str:
    if len(xs) == 1:
        return fmt.format(xs[0])
    return f'{fmt.format(float(np.median(xs)))} ({fmt.format(min(xs))}–{fmt.format(max(xs))})'


def _forecasts(path: Path) -> dict[str, np.ndarray]:
    """Forecast arrays keyed by method and column, without the worker count (it can differ between repetitions).
    prophet-batch: the n_jobs=1 run when it covers every series (bit-identical to n_jobs=many), else n_jobs=many."""
    with np.load(path) as z:
        out: dict[str, np.ndarray] = {}
        keys = [k for k in z.files if k.startswith(('stock_pool', 'batch'))]
        for k in sorted(keys, key=lambda k: k.rsplit('_', 2)[1] == '1'):  # n_jobs=1 last, so it wins
            method, _, col = k.rsplit('_', 2)
            out[f'{method}_{col}'] = z[k]
        return out


def group(r: dict[str, Any]) -> str:
    return r['machine'].get('dataset') or r['machine']['model']


def load(d: Path) -> dict[str, list[dict[str, Any]]]:
    runs: dict[str, list[dict[str, Any]]] = {}
    for f in sorted(d.glob('*.json'), key=lambda p: p.stem.rsplit('-', 2)[-2:]):
        r = json.loads(f.read_text(encoding='utf-8'))
        r['_npz'] = f.with_suffix('.npz')
        runs.setdefault(group(r), []).append(r)
    return runs


def summary(d: Path) -> str:
    runs = load(d)
    models = [m for m in ORDER if m in runs] + sorted(m for m in runs if m not in ORDER)
    first = runs[models[0]][0]
    mi, n = first['machine'], first['n']
    reps = sorted({len(runs[m]) for m in models})
    sizes = {runs[m][0]['n'] for m in models}
    count = f'{n:,} items · ' if len(sizes) == 1 else ''
    lines = [f'# Benchmark: {d.name}', '',
             f"{count}{', '.join(f'{m} × {len(runs[m])}' for m in models)} runs · {mi['cpu']} "
             f"({mi['logical_cpus']} logical CPUs, {mi['available_cpus']} available) · {mi['platform']} · "
             f"Python {mi['python']} · prophet {mi['versions']['prophet']} · prophet-batch {prophet_batch_label(mi)}"
             f" · examples {mi['commits']['prophet-batch-examples']}", '']
    if len(reps) > 1:
        lines += [f'Note: unequal repetitions per model ({reps}).', '']

    lines += ['## Speed: seconds for all items (fit + forecast), median (min–max) over repetitions', '']
    for m in models:
        rs = runs[m]
        per_rep = [max(row['workers'] for row in r['rows']) for r in rs]
        workers = f'{per_rep[0]} workers' if len(set(per_rep)) == 1 else f"workers {'/'.join(map(str, per_rep))} by repetition"
        size = '' if len(sizes) == 1 else f"{rs[0]['n']:,} series, "
        lines += [f'### {MODEL_LABEL.get(m, m)} ({size}{workers})', '',
                  '| method | workers | fit s | forecast s | total s | vs stock pool |', '|---|---:|---:|---:|---:|---:|']
        for i, row in enumerate(rs[0]['rows']):
            same = [r['rows'][i] for r in rs]
            pool = [next(x['total_s'] for x in r['rows'] if x['method'] == 'stock_pool') for r in rs]
            speed = [p / x['total_s'] for p, x in zip(pool, same)]
            label = METHOD_LABEL.get(row['method'], row['method'])
            lines.append(f"| {label} | {row['workers']} | {_stat([x['fit_s'] for x in same])} | "
                         f"{_stat([x['predict_s'] for x in same])} | {_stat([x['total_s'] for x in same])} | "
                         f"{_stat(speed, '{:.1f}')}× |")
        lines.append('')
    lines += ['¹ Timed on a sample (30 items), extrapolated. With different worker counts by repetition, the workers '
              'column shows the first repetition\'s.', '']

    held = 'the 28 held-out days' if 'dataset' not in mi else 'the held-out steps of each dataset'
    lines += [f'## Accuracy on {held} (first repetition)', '',
              '| model | method | WAPE | sMAPE | MASE | Δ MASE vs stock (± 2 SE) | 80% coverage |',
              '|---|---|---:|---:|---:|---:|---:|']
    for m in models:
        for row in runs[m][0]['rows']:
            if 'accuracy' not in row:
                continue
            a, dm = row['accuracy'], row.get('mase_vs_stock')
            delta = f"{dm['mean']:+.4f} ± {2 * dm['se']:.4f}" if dm else '–'
            lines.append(f"| {m} | {METHOD_LABEL.get(row['method'], row['method'])} | {a['wape']:.4f} | "
                         f"{a['smape']:.2f} | {a['mase']:.4f} | {delta} | {a['coverage']:.3f} |")
    lines.append('')

    lines += ['## Checks', '']
    for m in models:
        rs = runs[m]
        keys = list(rs[0]['checks'])
        bit = all(v is True for r in rs for k, v in r['checks'].items() if 'bit-identical' in k)
        lp = min(float(r['checks'][k]) for r in rs for k in keys if k.startswith('log posterior ≥'))
        fb = sorted({v for r in rs for k, v in r['checks'].items() if k.startswith('series fit by Stan')})
        base = _forecasts(rs[0]['_npz'])
        diff: dict[str, float] = {}
        for r in rs[1:]:
            other = _forecasts(r['_npz'])
            for k, v in base.items():
                kind = 'stock' if k.startswith('stock') else 'prophet-batch'
                d = float(np.max(np.abs(v - other[k]))) if k in other else float('inf')
                diff[kind] = max(diff.get(kind, 0.0), d)
        rep = ', '.join(f"{k} {'identical' if v == 0 else f'max |Δ| {v:.2g}'}" for k, v in diff.items()) or 'one repetition'
        lines.append(f'- {m}: n_jobs=1 vs many bit-identical in every run: {"yes" if bit else "NO"}; log posterior ≥ '
                     f"Stan's: min share {lp:.4f}; fallbacks: {', '.join(fb)}; forecasts across repetitions: {rep}.")
    return '\n'.join(lines) + '\n'


def main() -> int:
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[union-attr]
    print(summary(Path(sys.argv[1])), end='')
    return 0


if __name__ == '__main__':
    sys.exit(main())
