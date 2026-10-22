"""Run records and accuracy shared by every use case: machine and package info (incl. where prophet-batch came from),
holdout metrics per series, and helpers to align results.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from importlib.metadata import distribution, version
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .forecast import Result
from .metrics import coverage, mase, smape, wape_parts

REPO = Path(__file__).resolve().parents[1]


def _cmd(*args: str) -> str | None:
    try:
        return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def available_cpus(cgroup: Path = Path('/sys/fs/cgroup')) -> int:
    """CPUs this process may use: the affinity set, capped by a container's CPU quota (cgroup v2 cpu.max, or v1 CFS
    as on Cloud Run), which os.cpu_count() ignores. Same rule as prophet-batch's n_jobs=-1, so both sides get the same
    worker count.
    """
    n = len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else (os.cpu_count() or 1)
    for quota_file, period_file in ((cgroup / 'cpu.max', None),
                                    (cgroup / 'cpu' / 'cpu.cfs_quota_us', cgroup / 'cpu' / 'cpu.cfs_period_us')):
        try:
            text = quota_file.read_text().split()
            quota, period = (text[0], text[1]) if period_file is None else (text[0], period_file.read_text().strip())
            q, p = int(quota), int(period)
        except (OSError, ValueError, IndexError):  # missing, or 'max' (no quota)
            continue
        if q > 0 and p > 0:  # v1 uses -1 for no quota
            return max(1, min(n, -(-q // p)))
    return n


def _git_commit(path: Path) -> str | None:
    rev = _cmd('git', '-C', str(path), 'rev-parse', '--short', 'HEAD')
    dirty = _cmd('git', '-C', str(path), 'status', '--porcelain', '--untracked-files=no')
    return f'{rev}{"+dirty" if dirty else ""}' if rev else None


def prophet_batch_source() -> dict[str, str | None]:
    """Where prophet-batch came from: the package index (PyPI) or a local checkout (and its commit).

    Index installs carry no direct_url.json (PEP 610); local ones (editable checkout or a wheel built from one) do. In
    images built from a local checkout, PROPHET_BATCH_COMMIT names the commit the wheel was built from.
    """
    raw = distribution('prophet-batch').read_text('direct_url.json')
    if not raw:
        return {'source': 'pypi', 'commit': None}
    url = json.loads(raw).get('url', '')
    commit = os.environ.get('PROPHET_BATCH_COMMIT')
    if not commit and url.startswith('file://'):
        commit = _git_commit(Path(url.removeprefix('file://')))
    return {'source': 'local', 'commit': commit}


def prophet_batch_label(info: dict[str, Any]) -> str:
    """'0.1.1 (PyPI)' or '0.1.1 (local abc1234)'; older records have only a commit."""
    v, src = info['versions']['prophet-batch'], info.get('prophet_batch')
    if src is None:
        return f"{v} ({info['commits']['prophet-batch']})"
    return f'{v} (PyPI)' if src['source'] == 'pypi' else f"{v} (local {src['commit']})"


def _linux_cpu() -> str | None:
    try:
        for line in Path('/proc/cpuinfo').read_text().splitlines():
            if line.startswith('model name'):
                return line.split(':', 1)[1].strip()
    except OSError:
        pass
    return None


def machine_info() -> dict[str, Any]:
    pb = prophet_batch_source()
    return {
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'platform': platform.platform(),
        'cpu': (_cmd('sysctl', '-n', 'machdep.cpu.brand_string') or _linux_cpu() or platform.processor()
                or platform.machine()),
        'container': Path('/.dockerenv').exists(),
        'logical_cpus': os.cpu_count(),
        'available_cpus': available_cpus(),
        'python': sys.version.split()[0],
        'versions': {p: version(p) for p in ('prophet', 'prophet-batch', 'cmdstanpy', 'numpy', 'pandas')},
        'prophet_batch': pb,
        'commits': {'prophet-batch-examples': os.environ.get('EXAMPLES_COMMIT') or _git_commit(REPO),
                    'prophet-batch': pb['commit']},
        'thread_env': {v: os.environ.get(v) for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                                                      'VECLIB_MAXIMUM_THREADS')},
    }


def evaluate(r: Result, train: pd.DataFrame, test: pd.DataFrame, season: int) -> dict[str, Any]:
    """Per-series metrics (in train's row order; train and test: one row per series, one column per date) and their
    summary. `season` is MASE's seasonal period."""
    pos = {sid: i for i, sid in enumerate(r.ids)}
    err = scale = 0.0
    sm, ms, cov = [], [], []
    for sid in train.index:
        i, y = pos[sid], test.loc[sid].dropna().to_numpy()
        e, s = wape_parts(y, r.yhat[i])
        err, scale = err + e, scale + s
        sm.append(smape(y, r.yhat[i]))
        ms.append(mase(y, r.yhat[i], train.loc[sid].dropna().to_numpy(), season))
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



def utf8_stdout() -> None:
    """Print the summaries' symbols (Δ × ± ·) on any console: Windows defaults to cp1252 when output is redirected."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
