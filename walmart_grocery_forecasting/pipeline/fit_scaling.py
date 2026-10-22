"""How fit_many's time scales with worker count on this machine, and whether BLAS threading is the cause of poor
scaling (one model variant, all 1,437 items unless --n). Each setting runs in a fresh subprocess, so the BLAS thread
environment variables take effect before numpy loads.

    uv run python -m walmart_grocery_forecasting.pipeline.fit_scaling --model events_snap --jobs 1,4,16
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

THREAD_VARS = ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')


def one(model: str, n: int, jobs: int) -> dict:
    """Runs in the subprocess: fit_many once, timed."""
    import logging

    import numpy as np
    from prophet_batch import fit_many

    from . import data
    from .models import ModelSpec

    logging.getLogger('cmdstanpy').disabled = True
    train, _ = data.split(data.load_items())
    if n:
        train = train.iloc[:n]
    spec = ModelSpec(model, data.DATA_DIR)
    long_df = spec.with_regressors(data.to_long(train))
    kwargs = {'make_model': spec} if spec.regressors else spec.kwargs()
    t0 = time.perf_counter()
    fit_many(long_df, n_jobs=jobs, **kwargs)
    seconds = time.perf_counter() - t0
    blas = None
    try:  # which BLAS numpy uses, and its thread count
        from threadpoolctl import threadpool_info
        blas = [{k: d.get(k) for k in ('internal_api', 'num_threads', 'architecture')} for d in threadpool_info()]
    except ImportError:
        cfg = np.show_config(mode='dicts') if hasattr(np, 'show_config') else {}
        blas = cfg.get('Build Dependencies', {}).get('blas') if isinstance(cfg, dict) else None
    return {'model': model, 'n': len(train), 'jobs': jobs, 'seconds': seconds, 'blas': blas,
            'threads_env': {v: os.environ.get(v) for v in THREAD_VARS}}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--model', default='events_snap')
    p.add_argument('--jobs', default='1,4,16', help='comma-separated n_jobs values')
    p.add_argument('--n', type=int, default=0, help='first n items (default: all)')
    p.add_argument('--one', nargs=3, metavar=('MODEL', 'N', 'JOBS'), help=argparse.SUPPRESS)
    a = p.parse_args()
    if a.one:  # inside the subprocess
        print('RESULT ' + json.dumps(one(a.one[0], int(a.one[1]), int(a.one[2]))), flush=True)
        return 0
    rows = []
    for threads in (None, '1'):
        env = dict(os.environ)
        for v in THREAD_VARS:
            env.pop(v, None)
            if threads:
                env[v] = threads
        for jobs in (int(j) for j in a.jobs.split(',')):
            out = subprocess.run([sys.executable, '-m', 'walmart_grocery_forecasting.pipeline.fit_scaling', '--one',
                                  a.model, str(a.n), str(jobs)], env=env, capture_output=True, text=True,
                                 encoding='utf-8')
            line = next((ln for ln in out.stdout.splitlines() if ln.startswith('RESULT ')), None)
            if line is None:
                print(out.stdout[-2000:], out.stderr[-2000:])
                return 1
            r = json.loads(line[7:])
            rows.append(r)
            print(f"BLAS threads {threads or 'default':>7}  n_jobs {jobs:>2}: fit_many {r['seconds']:7.1f} s", flush=True)
    print('BLAS:', json.dumps(rows[0]['blas']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
