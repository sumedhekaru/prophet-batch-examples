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
import queue
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from examples_core.records import (MemoryRecorder, available_cpus, footprint_gb, machine_info, prophet_batch_label,
                                   utf8_stdout)

COLUMNS = ['ds', 'yhat', 'yhat_lower', 'yhat_upper']
_DONE = object()


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
    memory = MemoryRecorder()
    memory.step('stream')
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
                  f'memory {footprint_gb():.2f} GB', flush=True)
        to_write.put(_DONE)
    for th in threads:
        th.join()
    total = time.perf_counter() - t_start
    memory_record = memory.stop()
    info = machine_info()
    stage = {k: sum(s for kind, _, s in log if kind == k) for k in ('read', 'forecast', 'write')}
    stream = memory_record['steps']['stream']
    peak, worker_peak, workers_total = stream['parent_peak_gb'], stream['worker_peak_gb'], stream['workers_total_peak_gb']
    record: dict[str, Any] = {
        'machine': info, 'input': str(a.csv), 'input_mb': a.csv.stat().st_size / 1e6, 'meta': meta,
        'series': series, 'skipped_batches': skipped, 'series_per_batch': a.series_per_batch, 'workers': a.workers,
        'seconds': total, 'stage_seconds': stage, 'peak_gb': peak, 'worker_peak_gb': worker_peak,
        'workers_total_peak_gb': workers_total, 'memory': memory_record, 'log': log}
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    runs = Path(__file__).resolve().parent / 'results' / 'runs'
    runs.mkdir(parents=True, exist_ok=True)
    (runs / f'{a.csv.stem}-{stamp}.json').write_text(json.dumps(record, default=str), encoding='utf-8')
    print(f'\n{series:,} series from {a.csv.name} ({record["input_mb"]:,.0f} MB) in {total:.1f} s '
          f'({series / total:,.0f} series/s); stages (summed, they overlap): read {stage["read"]:.1f} s, '
          f'forecast {stage["forecast"]:.1f} s, write {stage["write"]:.1f} s; peak memory {peak:.2f} GB '
          f'({"largest worker " + format(worker_peak, ".2f") + " GB, all workers " + format(workers_total, ".2f") + " GB" if worker_peak is not None else "workers not measured"}); '
          f'prophet-batch {prophet_batch_label(info)}; {skipped} batch(es) already done')
    return 0


if __name__ == '__main__':
    sys.exit(main())
