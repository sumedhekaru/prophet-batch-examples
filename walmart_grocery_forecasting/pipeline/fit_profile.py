"""Profile fit_many in one process (n_jobs=1) on this machine: where does the time go? Prints the top functions by
cumulative and by own time, and a few coarse phases (preprocessing, solver, other), and saves the raw profile.

    uv run python -m walmart_grocery_forecasting.pipeline.fit_profile --model default --n 200
"""

from __future__ import annotations

import argparse
import cProfile
import io
import logging
import platform
import pstats
import sys
import time
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--model', default='default')
    p.add_argument('--n', type=int, default=200, help='first n items (default 200)')
    p.add_argument('--top', type=int, default=25)
    a = p.parse_args()

    from prophet_batch import fit_many

    from . import data
    from .models import ModelSpec
    from .run import utf8_stdout

    utf8_stdout()
    logging.getLogger('cmdstanpy').disabled = True
    train, _ = data.split(data.load_items())
    train = train.iloc[:a.n]
    spec = ModelSpec(a.model, data.DATA_DIR)
    long_df = spec.with_regressors(data.to_long(train))
    kwargs = {'make_model': spec} if spec.regressors else spec.kwargs()

    prof = cProfile.Profile()
    t0 = time.perf_counter()
    prof.enable()
    fit_many(long_df, n_jobs=1, **kwargs)
    prof.disable()
    total = time.perf_counter() - t0

    out = Path(__file__).resolve().parents[1] / 'results' / 'runs'
    out.mkdir(parents=True, exist_ok=True)
    raw = out / f'fit-profile-{platform.system().lower()}-{a.model}-{a.n}.prof'
    prof.dump_stats(str(raw))
    stats = pstats.Stats(prof)
    print(f'fit_many, {a.model}, {a.n} items, n_jobs=1: {total:.1f} s on {platform.platform()}, '
          f'Python {platform.python_version()}')

    # coarse phases: cumulative time of a few known entry points
    phases = {'preprocess (Prophet)': 'preprocess', 'shared preprocess': '_preprocess_shared',
              'design matrix': 'design_matrix', 'additive solver': 'solve_map', 'holiday features': 'make_holiday_features',
              'seasonality features': 'make_all_seasonality_features', 'pandas to_datetime': 'to_datetime',
              'deepcopy': 'deepcopy'}
    for label, fn in phases.items():
        cum = sum(v[3] for k, v in stats.stats.items() if k[2] == fn)
        print(f'  {label:24s} {cum:7.2f} s  ({100 * cum / total:4.1f}%)')
    for key in ('cumulative', 'tottime'):
        buf = io.StringIO()
        pstats.Stats(prof, stream=buf).sort_stats(key).print_stats(a.top)
        text = buf.getvalue()
        print(f'\n=== top {a.top} by {key}\n' + text[text.find('   ncalls'):].rstrip())
    print(f'\nraw profile: {raw}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
