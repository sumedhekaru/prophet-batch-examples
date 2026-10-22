"""Forecast a large CSV of series in batches: read, forecast and write at the same time, with flat memory.

    uv run python -m streaming_csv.run data/streaming/m5_item-x1.csv              # writes data/streaming/<name>-out/
    uv run python -m streaming_csv.run data/streaming/m5_item-x4.csv --series-per-batch 2000 --workers 10

The pattern (all of it here, in plain sight: prophet-batch only computes):

    reader thread  --[queue: ≤ 2 batches]-->  main thread: Pool.forecast_many  --[queue: ≤ 2]-->  writer thread
    pd.read_csv(chunksize=...)                fit + forecast each batch on                      one CSV part per
    whole series per chunk                    workers kept for the whole run                    batch (part-00007.csv)

- The input is the prepared CSV (prepare.py): rows grouped by series, every series the same length, so a chunk of
  rows_per_series × series_per_batch rows always holds whole series.
- Memory: at most ≈ 5 batches exist at once (2 read ahead, 1 computing, 2 waiting to be written), whatever the file
  size. The run record shows the peak.
- Restart: a part that already exists is not forecast again (its batch is read and skipped), so a crashed run resumes
  where it stopped. Delete the output directory to start over.
- Output: ds, yhat, yhat_lower, yhat_upper for the horizon only (include_history=False, analytic history intervals
  not needed then): the usual production output; change COLUMNS / the forecast_many arguments for stock's full frame.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from examples_core.records import available_cpus, machine_info, prophet_batch_label, utf8_stdout

COLUMNS = ['ds', 'yhat', 'yhat_lower', 'yhat_upper']
_DONE = object()


def _windows_working_set_gb() -> float:
    """This process's working set (GetProcessMemoryInfo), in GB."""
    import ctypes
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD),
                    ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
                    ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t), ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                    ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t)]

    counters = Counters()
    counters.cb = ctypes.sizeof(Counters)
    kernel32 = getattr(ctypes, 'windll').kernel32
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    get_info = kernel32.K32GetProcessMemoryInfo
    get_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    get_info.restype = wintypes.BOOL
    if not get_info(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        return float('nan')
    return counters.WorkingSetSize / 1e9


def _footprint_gb() -> float:
    """This process's memory in GB: physical footprint on macOS (incl. compressed pages), the working set on
    Windows, RSS elsewhere."""
    if sys.platform == 'win32':
        try:
            return _windows_working_set_gb()
        except Exception:
            return float('nan')
    if sys.platform == 'darwin':
        import ctypes
        buf = (ctypes.c_uint64 * 48)()
        if ctypes.CDLL('/usr/lib/libproc.dylib').proc_pid_rusage(os.getpid(), 4, ctypes.byref(buf)) == 0:
            return buf[2 + 7] / 1e9
    try:
        with open('/proc/self/status') as f:
            for line in f:
                if line.startswith('VmRSS:'):
                    return int(line.split()[1]) * 1024 / 1e9
    except OSError:
        pass
    return float('nan')


class MemorySampler(threading.Thread):
    """Samples this process's memory every 0.2 s: (seconds since start, GB)."""

    def __init__(self) -> None:
        super().__init__(daemon=True)
        self.t0, self.samples, self.stop = time.perf_counter(), [], threading.Event()

    def run(self) -> None:
        while not self.stop.is_set():
            self.samples.append((time.perf_counter() - self.t0, _footprint_gb()))
            self.stop.wait(0.2)


def reader(path: Path, chunk_rows: int, out: queue.Queue, log: list) -> None:
    """Read whole-series chunks and queue them (blocks when 2 are waiting)."""
    t = time.perf_counter()
    for i, chunk in enumerate(pd.read_csv(path, chunksize=chunk_rows, parse_dates=['ds'])):
        log.append(('read', i, time.perf_counter() - t))
        out.put((i, chunk))
        t = time.perf_counter()
    out.put(_DONE)


def writer(out_dir: Path, inp: queue.Queue, log: list) -> None:
    """Write each forecast batch as its own CSV part (written to a temporary name, then renamed)."""
    while (item := inp.get()) is not _DONE:
        i, fc = item
        t = time.perf_counter()
        tmp = out_dir / f'part-{i:05d}.csv.tmp'
        fc.to_csv(tmp, index=False, date_format='%Y-%m-%d')
        tmp.replace(out_dir / f'part-{i:05d}.csv')
        log.append(('write', i, time.perf_counter() - t))


def main() -> int:
    utf8_stdout()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('csv', type=Path, help='prepared CSV (prepare.py) with its .json next to it')
    p.add_argument('--series-per-batch', type=int, default=1000)
    p.add_argument('--workers', type=int, default=available_cpus())
    p.add_argument('--out', type=Path, default=None, help='output directory (default: <csv name>-out/)')
    p.add_argument('--seed', type=int, default=0)
    a = p.parse_args()
    from prophet_batch import Pool

    meta = json.loads(a.csv.with_suffix('.json').read_text())
    out_dir = a.out or a.csv.with_name(a.csv.stem + '-out')
    out_dir.mkdir(parents=True, exist_ok=True)
    chunk_rows = meta['rows_per_series'] * a.series_per_batch
    sampler = MemorySampler()
    sampler.start()
    to_compute: queue.Queue = queue.Queue(maxsize=2)
    to_write: queue.Queue = queue.Queue(maxsize=2)
    log: list[tuple[str, int, float]] = []
    t_start = time.perf_counter()
    threads = [threading.Thread(target=reader, args=(a.csv, chunk_rows, to_compute, log), daemon=True),
               threading.Thread(target=writer, args=(out_dir, to_write, log), daemon=True)]
    for th in threads:
        th.start()
    series = skipped = 0
    with Pool(n_jobs=a.workers) as pool:
        while (item := to_compute.get()) is not _DONE:
            i, batch = item
            series += batch['unique_id'].nunique()
            if (out_dir / f'part-{i:05d}.csv').exists():
                skipped += 1
                continue
            t = time.perf_counter()
            fc = pool.forecast_many(batch, periods=meta['horizon'], freq=meta['freq'], seed=a.seed,
                                    include_history=False, columns=COLUMNS)
            log.append(('forecast', i, time.perf_counter() - t))
            to_write.put((i, fc))
            print(f'batch {i:5d}: {batch["unique_id"].nunique():,} series forecast in {log[-1][2]:.1f} s; '
                  f'memory {_footprint_gb():.2f} GB', flush=True)
        to_write.put(_DONE)
    for th in threads:
        th.join()
    total = time.perf_counter() - t_start
    sampler.stop.set()
    sampler.join()

    info = machine_info()
    stage = {k: sum(s for kind, _, s in log if kind == k) for k in ('read', 'forecast', 'write')}
    peak = max(gb for _, gb in sampler.samples)
    worker_peak = None  # the pool's workers have exited: their peaks are in RUSAGE_CHILDREN (POSIX only)
    try:
        import resource
        child = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        worker_peak = (child if sys.platform == 'darwin' else child * 1024) / 1e9
    except ImportError:  # Windows: not measured
        pass
    record: dict[str, Any] = {
        'machine': info, 'input': str(a.csv), 'input_mb': a.csv.stat().st_size / 1e6, 'meta': meta,
        'series': series, 'skipped_batches': skipped, 'series_per_batch': a.series_per_batch, 'workers': a.workers,
        'seconds': total, 'stage_seconds': stage, 'peak_gb': peak, 'worker_peak_gb': worker_peak, 'memory': sampler.samples, 'log': log}
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    runs = Path(__file__).resolve().parent / 'results' / 'runs'
    runs.mkdir(parents=True, exist_ok=True)
    (runs / f'{a.csv.stem}-{stamp}.json').write_text(json.dumps(record, default=str), encoding='utf-8')
    print(f'\n{series:,} series from {a.csv.name} ({record["input_mb"]:,.0f} MB) in {total:.1f} s '
          f'({series / total:,.0f} series/s); stages (summed, they overlap): read {stage["read"]:.1f} s, '
          f'forecast {stage["forecast"]:.1f} s, write {stage["write"]:.1f} s; peak memory {peak:.2f} GB '
          f'({"each worker ≤ " + format(worker_peak, ".2f") + " GB" if worker_peak is not None else "workers not measured"}); '
          f'prophet-batch {prophet_batch_label(info)}; {skipped} batch(es) already done')
    return 0


if __name__ == '__main__':
    sys.exit(main())
