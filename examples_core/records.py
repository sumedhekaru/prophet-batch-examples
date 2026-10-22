"""Run records and accuracy shared by every use case: machine and package info (incl. where prophet-batch came from),
holdout metrics per series, and helpers to align results.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
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
    if not commit and url.startswith('file:'):
        # file:///C:/... on Windows: url2pathname turns the URL path into C:\...
        from urllib.parse import unquote, urlparse
        from urllib.request import url2pathname
        commit = _git_commit(Path(url2pathname(unquote(urlparse(url).path))))
    return {'source': 'local', 'commit': commit}


def prophet_batch_label(info: dict[str, Any]) -> str:
    """'0.1.1 (PyPI)' or '0.1.1 (local abc1234)'; older records have only a commit."""
    v, src = info['versions']['prophet-batch'], info.get('prophet_batch')
    if src is None:
        return f"{v} ({info['commits']['prophet-batch']})"
    return f'{v} (PyPI)' if src['source'] == 'pypi' else f"{v} (local {src['commit']})"


def _windows_cpu() -> str | None:
    """The CPU's marketing name from the registry (platform.processor() gives only "Intel64 Family 6 ...")."""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\CentralProcessor\0')
        return str(winreg.QueryValueEx(key, 'ProcessorNameString')[0]).strip()
    except Exception:
        return None


def memory_total_gb() -> float | None:
    """The machine's physical memory in GB (inside a container: the host's, see memory_limit in the record)."""
    try:
        if sys.platform == 'win32':
            import ctypes

            class Status(ctypes.Structure):
                _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong),
                            ('ullTotalPhys', ctypes.c_ulonglong), ('ullAvailPhys', ctypes.c_ulonglong),
                            ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong),
                            ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong),
                            ('ullAvailExtendedVirtual', ctypes.c_ulonglong)]

            st = Status()
            st.dwLength = ctypes.sizeof(Status)
            if getattr(ctypes, 'windll').kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):
                return st.ullTotalPhys / 1e9
            return None
        return os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') / 1e9
    except (OSError, ValueError, AttributeError):
        return None


def memory_limit_gb() -> float | None:
    """A container's memory limit (cgroup v2 memory.max or v1), in GB; None when there is none."""
    for path in ('/sys/fs/cgroup/memory.max', '/sys/fs/cgroup/memory/memory.limit_in_bytes'):
        try:
            value = int(Path(path).read_text().strip())
        except (OSError, ValueError):
            continue
        return value / 1e9 if value < 1 << 60 else None
    return None


def footprint_gb() -> float:
    """This process's memory now, in GB: macOS physical footprint (incl. compressed pages: RSS drops when macOS
    compresses), Windows working set, Linux RSS; NaN when it can't be read."""
    try:
        if sys.platform == 'darwin':
            import ctypes
            buf = (ctypes.c_uint64 * 48)()
            if ctypes.CDLL('/usr/lib/libproc.dylib').proc_pid_rusage(os.getpid(), 4, ctypes.byref(buf)) == 0:
                return buf[2 + 7] / 1e9
        elif sys.platform == 'win32':
            import ctypes
            from ctypes import wintypes

            class Counters(ctypes.Structure):
                _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD),
                            ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
                            ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
                            ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                            ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                            ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t)]

            c = Counters()
            c.cb = ctypes.sizeof(Counters)
            k32 = getattr(ctypes, 'windll').kernel32
            k32.GetCurrentProcess.restype = wintypes.HANDLE
            fn = k32.K32GetProcessMemoryInfo
            fn.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
            fn.restype = wintypes.BOOL
            if fn(k32.GetCurrentProcess(), ctypes.byref(c), c.cb):
                return c.WorkingSetSize / 1e9
        else:
            with open('/proc/self/status') as f:
                for line in f:
                    if line.startswith('VmRSS:'):
                        return int(line.split()[1]) * 1024 / 1e9
    except Exception:
        pass
    return float('nan')


def descendants_rss_gb() -> tuple[float, float] | None:
    """(largest, total) resident memory of this process's descendants (worker processes, Stan runs), in GB, read
    now: /proc on Linux, ps on macOS; None elsewhere (Windows) or when it can't be read. RUSAGE_CHILDREN is not
    used for this: on Linux a fork+exec'd child is charged the parent's size at fork time."""
    me = os.getpid()
    try:
        procs: dict[int, tuple[int, int]] = {}  # pid -> (ppid, rss bytes)
        if sys.platform.startswith('linux'):
            for entry in os.listdir('/proc'):
                if not entry.isdigit():
                    continue
                try:
                    with open(f'/proc/{entry}/stat') as f:
                        stat = f.read()
                    ppid = int(stat[stat.rindex(')') + 2:].split()[1])
                    rss_pages = int(stat[stat.rindex(')') + 2:].split()[21])
                    procs[int(entry)] = (ppid, rss_pages * os.sysconf('SC_PAGE_SIZE'))
                except (OSError, ValueError, IndexError):
                    continue
        elif sys.platform == 'darwin':
            out = subprocess.run(['ps', '-A', '-o', 'pid=,ppid=,rss='], capture_output=True, text=True, timeout=5).stdout
            for line in out.splitlines():
                pid, ppid, rss = (int(x) for x in line.split())
                procs[pid] = (ppid, rss * 1024)
        else:
            return None
    except Exception:
        return None
    children: dict[int, list[int]] = {}
    for pid, (ppid, _) in procs.items():
        children.setdefault(ppid, []).append(pid)
    stack, found = list(children.get(me, [])), []
    while stack:
        pid = stack.pop()
        found.append(procs[pid][1])
        stack.extend(children.get(pid, []))
    found = [b for b in found if b > 0]
    return (max(found) / 1e9, sum(found) / 1e9) if found else (0.0, 0.0)


def children_peak_gb() -> float | None:
    """The largest peak RSS of any child process that has exited (worker processes), in GB; None on Windows."""
    try:
        import resource
    except ImportError:
        return None
    rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    return (rss if sys.platform == 'darwin' else rss * 1024) / 1e9


class MemoryRecorder:
    """Samples this process's memory every 0.2 s and its descendants' (workers, Stan runs) every ≈ 0.6 s in a
    thread; step(label) records each step's peaks: this process, the largest single descendant, and all descendants
    together."""

    def __init__(self, interval: float = 0.2) -> None:
        import threading
        self.interval, self.t0 = interval, time.perf_counter()
        self.samples: list[tuple[float, float]] = []
        self.steps: dict[str, dict[str, float | None]] = {}
        self._label: str | None = None
        self._peak = 0.0
        self._desc_max = self._desc_total = 0.0
        self._desc_ok = descendants_rss_gb() is not None
        self._ticks = 0
        # Children that exited before this run (e.g. a data step the container's entrypoint ran before exec'ing this
        # process) are in RUSAGE_CHILDREN already: worker peaks count only once they rise above this baseline.
        self.children_baseline = children_peak_gb()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.is_set():
            gb = footprint_gb()
            workers = None
            if self._desc_ok and self._ticks % 3 == 0:  # descendants every ~0.6 s (ps on macOS is a process)
                d = descendants_rss_gb()
                if d is not None:
                    self._desc_max, self._desc_total = max(self._desc_max, d[0]), max(self._desc_total, d[1])
                    workers = round(d[1], 4)
            self._ticks += 1
            self.samples.append((round(time.perf_counter() - self.t0, 2), round(gb, 4), workers))
            if gb == gb:
                self._peak = max(self._peak, gb)
            self._stop.wait(self.interval)

    def step(self, label: str | None) -> None:
        """End the current step (record its peak) and start `label` (None: just end)."""
        if self._label is not None:
            children = children_peak_gb()
            above = (children is not None and (self.children_baseline is None or children > self.children_baseline))
            self.steps[self._label] = {
                'parent_peak_gb': round(max(self._peak, footprint_gb()), 4),
                'worker_peak_gb': round(self._desc_max, 4) if self._desc_ok else None,       # largest one process
                'workers_total_peak_gb': round(self._desc_total, 4) if self._desc_ok else None,  # all at once
                'rusage_children_so_far_gb': round(children, 4) if above else None}  # raw; see descendants_rss_gb
        self._label, self._peak = label, footprint_gb()
        self._desc_max = self._desc_total = 0.0

    def stop(self) -> dict[str, Any]:
        self.step(None)
        self._stop.set()
        self._thread.join()
        every = max(1, len(self.samples) // 2000)  # keep at most ≈ 2,000 samples in the record
        return {'how': ('physical footprint' if sys.platform == 'darwin' else
                        'working set' if sys.platform == 'win32' else 'RSS'),
                'workers_how': ('RSS of every descendant process, sampled ≈ every 0.6 s' if self._desc_ok
                                else 'not measured on this platform'),
                'timeline_columns': ['seconds', 'main process GB', 'all descendants GB (when sampled)'],
                'children_baseline_gb': self.children_baseline, 'steps': self.steps,
                'timeline': self.samples[::every]}


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
        'cpu': (_cmd('sysctl', '-n', 'machdep.cpu.brand_string') or _linux_cpu() or _windows_cpu()
                or platform.processor() or platform.machine()),
        'memory_total_gb': memory_total_gb(),
        'memory_limit_gb': memory_limit_gb(),
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
