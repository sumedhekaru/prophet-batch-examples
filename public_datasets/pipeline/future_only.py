"""Future rows only: stock Prophet's fastest setup vs prophet-batch, when forecasts of the history are not needed.

    uv run python -m public_datasets.pipeline.future_only                       # the three large datasets, 3 runs
    uv run python -m public_datasets.pipeline.future_only --datasets m4_daily --n 100 --reps 1

run.py forecasts the history plus the held-out steps, as `model.predict(model.make_future_dataframe(h))` does; most of
stock Prophet's predict time then goes into simulating intervals for every history row. A user who only needs the
future can ask stock Prophet for the future rows only (`make_future_dataframe(h, include_history=False)`), which
removes that work. This compares the two methods on that setup: a stock process pool forecasting the future rows only,
and `forecast_many(..., include_history=False)` (same rows, same interval columns, default settings otherwise). Both
fit every series in full. Writes results/runs/future-only-<env>-<timestamp>.{json,md}.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from examples_core.forecast import run_forecast_many, run_stock_pool
from examples_core.records import available_cpus, evaluate, machine_info, paired, prophet_batch_label, utf8_stdout

from . import data
from .run import RUNS, DefaultSpec

BIG3 = ['m5_item_store', 'm4_daily', 'm5_item']


def one(ds: data.Dataset, workers: int) -> dict[str, Any]:
    h, spec = ds.horizon, DefaultSpec(ds.freq)
    series = {sid: g[['ds', 'y']].reset_index(drop=True) for sid, g in ds.train.groupby('unique_id', sort=False)}
    stock = run_stock_pool(series, h, spec, workers, include_history=False)
    batch = run_forecast_many(ds.train, h, spec, workers, include_history=False)[0]
    sa, ba = evaluate(stock, ds.train_wide, ds.test_wide, ds.season), evaluate(batch, ds.train_wide, ds.test_wide, ds.season)
    return {'stock_s': stock.total_s, 'stock_fit_s': stock.fit_s, 'stock_predict_s': stock.predict_s,
            'batch_s': batch.total_s, 'speedup': stock.total_s / batch.total_s,
            'mase': {'stock': sa['summary']['mase'], 'batch': ba['summary']['mase']},
            'coverage': {'stock': sa['summary']['coverage'], 'batch': ba['summary']['coverage']},
            'mase_vs_stock': paired(sa['per_series']['mase'], ba['per_series']['mase'])}


def main() -> int:
    utf8_stdout()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--datasets', default=','.join(BIG3))
    p.add_argument('--n', type=int, default=None, help='random sample of n series (default: all)')
    p.add_argument('--reps', type=int, default=3)
    p.add_argument('--workers', type=int, default=available_cpus())
    p.add_argument('--env', default='local')
    p.add_argument('--data-dir', type=Path, default=data.DATA_DIR)
    p.add_argument('--out', type=Path, default=RUNS)
    a = p.parse_args()
    names = a.datasets.split(',')
    loaded = {d: data.load(d, a.n, data_dir=a.data_dir) for d in names}
    runs: dict[str, list[dict[str, Any]]] = {d: [] for d in names}
    for rep in range(1, a.reps + 1):
        for d in names:
            r = one(loaded[d], a.workers)
            runs[d].append(r)
            print(f"{d} rep {rep}: stock (future only) {r['stock_s']:.1f} s, forecast_many (future only) "
                  f"{r['batch_s']:.1f} s: {r['speedup']:.1f}×", flush=True)
    info = machine_info()
    lines = ['# Future rows only: stock Prophet\'s fastest setup vs prophet-batch', '',
             f"{info['timestamp']} · {info['cpu']} ({info['logical_cpus']} logical CPUs) · {info['platform']} · "
             f"prophet {info['versions']['prophet']} · prophet-batch {prophet_batch_label(info)} · examples "
             f"{info['commits']['prophet-batch-examples']} · {a.workers} workers · {a.reps} runs: median (min–max)", '',
             '| dataset | series | stock pool, future rows only | `forecast_many(include_history=False)` | faster | '
             'MASE stock / prophet-batch | Δ MASE (± 2 SE) | 80% coverage stock / prophet-batch |',
             '|---|---:|---:|---:|---:|---|---:|---|']
    for d in names:
        rs = runs[d]
        st, bt, sp = (np.array([r[k] for r in rs]) for k in ('stock_s', 'batch_s', 'speedup'))
        r0 = rs[0]
        lines.append(f"| {d} | {len(loaded[d].train_wide):,} | {np.median(st):.1f} s ({st.min():.1f}–{st.max():.1f}) | "
                     f"{np.median(bt):.1f} s ({bt.min():.1f}–{bt.max():.1f}) | **{np.median(sp):.1f}×** "
                     f"({sp.min():.1f}–{sp.max():.1f}) | {r0['mase']['stock']:.4f} / {r0['mase']['batch']:.4f} | "
                     f"{r0['mase_vs_stock']['mean']:+.4f} ± {2 * r0['mase_vs_stock']['se']:.4f} | "
                     f"{r0['coverage']['stock']:.3f} / {r0['coverage']['batch']:.3f} |")
    md = '\n'.join(lines) + '\n'
    a.out.mkdir(parents=True, exist_ok=True)
    stem = a.out / f'future-only-{a.env}-{datetime.now():%Y%m%d-%H%M%S}'
    stem.with_suffix('.json').write_text(json.dumps({'machine': info, 'args': {k: str(v) for k, v in vars(a).items()},
                                                     'runs': runs}, indent=1, default=str), encoding='utf-8')
    stem.with_suffix('.md').write_text(md, encoding='utf-8')
    print('\n' + md + f'\nsaved {stem}.{{json,md}}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
