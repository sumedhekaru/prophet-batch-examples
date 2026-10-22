"""Summarize a Spark benchmark directory: phase times per method, speed-ups, parallelism used, accuracy, cost.

    uv run python -m walmart_grocery_forecasting.pipeline.spark_summary DIR > DIR/summary.md

DIR holds, per run, <id>.json + <id>.end.json from spark_job.py and, on Dataproc, <id>.batch.json (the batch resource:
create time, state history, end time, DCU usage). Phases (seconds):

  provision     batch created → RUNNING                       (platform; Dataproc only)
  driver_start  RUNNING → Spark session ready in the driver    (Dataproc only)
  executors     session ready → requested executors registered
  load          executors ready → data copied, loaded, cached
  warmup        Python workers started and Prophet imported on every core (--warmup; else –)
  execute       the method's Spark job: data in, models fit + forecast, results collected   ← speed-up basis
  post          results collected → accuracy computed, outputs written
  shutdown      outputs written → batch finished (Spark stop, platform teardown; Dataproc only)
  end_to_end    batch created → batch finished                (Dataproc only)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

from .run import prophet_batch_label

PHASES = ['provision', 'driver_start', 'executors', 'load', 'warmup', 'execute', 'post', 'shutdown', 'end_to_end']


def _ts(s: str) -> float:
    return datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()


def run_phases(rec: dict, end: dict, batch: dict | None) -> dict[str, float | None]:
    m = rec['marks']
    p: dict[str, float | None] = dict.fromkeys(PHASES)
    p['executors'] = m['executors_ready'] - m['session_ready']
    p['load'] = m['load_done'] - m['executors_ready']
    p['warmup'] = m['warmup_done'] - m['load_done'] if 'warmup_done' in m else None
    p['execute'] = m['execute_end'] - m['execute_start']
    p['post'] = end['write_end'] - m['execute_end']
    if batch:
        created = _ts(batch['createTime'])
        running = next((_ts(h['stateStartTime']) for h in batch.get('stateHistory', []) if h['state'] == 'RUNNING'),
                       None)
        if running is None:  # still RUNNING when described: the current state started then
            running = _ts(batch['stateTime']) if batch['state'] == 'RUNNING' else None
        finished = _ts(batch['stateTime'])
        p['provision'] = running - created if running else None
        p['driver_start'] = m['session_ready'] - running if running else None
        p['shutdown'] = finished - end['write_end']
        p['end_to_end'] = finished - created
    return p


def load(directory: Path) -> list[dict]:
    runs = []
    for f in sorted(directory.glob('*.json')):
        if f.name.endswith(('.end.json', '.batch.json')):
            continue
        rec = json.loads(f.read_text(encoding='utf-8'))
        if 'marks' not in rec:  # config.json and other non-run files
            continue
        end_f, batch_f = f.with_suffix('.end.json'), f.with_suffix('.batch.json')
        end = json.loads(end_f.read_text(encoding='utf-8')) if end_f.exists() else {'write_end': rec['marks']['write_start']}
        batch = json.loads(batch_f.read_text(encoding='utf-8')) if batch_f.exists() else None
        npz = np.load(f.with_suffix('.npz'))
        usage = ((batch or {}).get('runtimeInfo') or {}).get('approximateUsage') or {}
        dcu = int(usage['milliDcuSeconds']) / 1000 if 'milliDcuSeconds' in usage else None  # not reported by 2.x
        runs.append({'id': rec['run_id'], 'method': rec['method'], 'rec': rec, 'phases': run_phases(rec, end, batch),
                     'dcu_s': dcu, 'yhat': npz['yhat'], 'ids': list(npz['ids'])})
    return runs


def _stat(values: list[float]) -> str:
    v = [x for x in values if x is not None]
    if not v:
        return '–'
    f = (lambda x: f'{x:.0f}') if all(float(x).is_integer() for x in v) else (lambda x: f'{x:.1f}')
    if len(v) == 1:
        return f(v[0])
    return f'{f(np.median(v))} ({f(min(v))}–{f(max(v))})'


def summarize(directory: Path) -> str:
    runs = load(directory)
    methods = [m for m in ('stock', 'batch') if any(r['method'] == m for r in runs)]
    by = {m: [r for r in runs if r['method'] == m] for m in methods}
    first = runs[0]['rec']
    sp, mi = first['spark'], first['machine']
    lines = [f'# Spark benchmark: {directory.name}', '',
             f"{len(runs)} runs · {first['n']:,} items · Spark {sp['version']} · master `{sp['master']}` · "
             f"{sp['executors']} executors, parallelism {sp['default_parallelism']} · shuffle partitions "
             f"{sp.get('shuffle_partitions')} · prophet {mi['versions']['prophet']} · prophet-batch "
             f"{prophet_batch_label(mi)} · examples {mi['commits']['prophet-batch-examples']}", '',
             '## Phases (seconds: median, (min–max) over repetitions)', '',
             '| phase | ' + ' | '.join(f'{m} (n={len(by[m])})' for m in methods) + ' |',
             '|---|' + '---:|' * len(methods)]
    for ph in PHASES:
        lines.append(f'| {ph} | ' + ' | '.join(_stat([r['phases'][ph] for r in by[m]]) for m in methods) + ' |')
    if len(methods) == 2:
        lines += ['', '## Speed-up (stock / prophet-batch, medians)', '']
        for ph in ('execute', 'end_to_end'):
            s = [r['phases'][ph] for r in by['stock'] if r['phases'][ph] is not None]
            b = [r['phases'][ph] for r in by['batch'] if r['phases'][ph] is not None]
            if s and b:
                ratios = [x / y for x, y in zip(s, b)]
                lines.append(f'- **{ph}**: {np.median(s) / np.median(b):.1f}× (per repetition: '
                             + ', '.join(f'{x:.1f}×' for x in ratios) + ')')
    lines += ['', '## Parallelism used (from per-task records)', '',
              '| method | tasks | hosts | processes | max concurrent | core utilisation during execute |',
              '|---|---:|---:|---:|---:|---:|']
    for m in methods:
        t = [r['rec']['tasks'] for r in by[m]]
        lines.append(f"| {m} | {_stat([x['tasks'] for x in t])} | {_stat([x['hosts'] for x in t])} | "
                     f"{_stat([x['processes'] for x in t])} | {_stat([x['max_concurrent'] for x in t])} | "
                     f"{_stat([100 * x['core_utilisation'] for x in t])}% |")
    lines += ['', '## Accuracy and reproducibility', '',
              '| method | WAPE | MASE | 80% coverage | forecasts identical across repetitions |', '|---|---:|---:|---:|---|']
    for m in methods:
        a = by[m][0]['rec']['accuracy']
        same = all(np.array_equal(by[m][0]['yhat'], r['yhat']) for r in by[m])
        lines.append(f"| {m} | {a['wape']:.4f} | {a['mase']:.4f} | {a['coverage']:.3f} | {same} |")
    if all(r['dcu_s'] is not None for r in runs):
        lines += ['', '## Cost (Dataproc DCU-seconds per run)', '']
        lines += [f"- {m}: {_stat([r['dcu_s'] for r in by[m]])}" for m in methods]
    lines += ['', '## Runs', '', '| run | method | ' + ' | '.join(PHASES) + ' |', '|---|---|' + '---:|' * len(PHASES)]
    for r in runs:
        lines.append(f"| {r['id']} | {r['method']} | " + ' | '.join(
            f"{r['phases'][ph]:.1f}" if r['phases'][ph] is not None else '–' for ph in PHASES) + ' |')
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    from .run import utf8_stdout

    utf8_stdout()
    print(summarize(Path(sys.argv[1])), end='')
