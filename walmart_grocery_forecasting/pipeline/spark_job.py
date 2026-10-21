"""The use case on Spark: one method per run, every phase timed, every task recorded (benchmark protocol, track F5).

    spark-submit spark_main.py --data DIR --out DIR --method batch|stock [--groups N] [--run-id ID]

  batch  items hashed into --groups groups; groupBy(group).applyInPandas runs fit_many + predict_many on each group
         (many series per task; history_uncertainty='analytic', only the interval columns returned)
  stock  groupBy(item).applyInPandas runs Prophet().fit + predict on each item (one series per task)
Both use all 1,437 items and forecast history + 28 days (as run.py). Phase timestamps (time.time(), UTC epoch):
script_start, session_ready, executors_ready, load_done, execute_start, execute_end, write_start, and write_end
(in <run-id>.end.json, written last). Provisioning and
shutdown come from the platform (Dataproc's batch state history); summarize.py combines them. Each output row carries
the task's host, pid, start and end, so the parallelism actually used is measured, not assumed.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import tempfile
import time
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

from . import data
from .forecast import Result
from .run import evaluate, machine_info

H = data.HORIZON
BANDS = ['yhat', 'yhat_lower', 'yhat_upper']
OUT_SCHEMA = ('unique_id string, step int, yhat double, yhat_lower double, yhat_upper double, lp double, '
              'host string, pid int, t0 double, t1 double')


def _quiet() -> None:
    import logging

    logging.getLogger('cmdstanpy').disabled = True
    logging.getLogger('prophet').setLevel(logging.WARNING)


def _rows(sid: str, bands: np.ndarray, lp: float, t0: float, t1: float) -> pd.DataFrame:
    return pd.DataFrame({'unique_id': sid, 'step': np.arange(H, dtype=np.int32), 'yhat': bands[0],
                         'yhat_lower': bands[1], 'yhat_upper': bands[2], 'lp': lp, 'host': socket.gethostname(),
                         'pid': os.getpid(), 't0': t0, 't1': t1})


def stock_item(pdf: pd.DataFrame) -> pd.DataFrame:
    """One item: Prophet().fit + predict (seeded like run.py's stock side)."""
    t0 = time.time()
    from prophet import Prophet

    _quiet()
    sid = str(pdf['unique_id'].iloc[0])
    m = Prophet().fit(pdf[['ds', 'y']].sort_values('ds'))
    np.random.seed(zlib.crc32(sid.encode()))
    fc = m.predict(m.make_future_dataframe(H)).tail(H)
    return _rows(sid, fc[BANDS].to_numpy().T, float(m.params['lp__'][0, 0]), t0, time.time())


def batch_group(pdf: pd.DataFrame) -> pd.DataFrame:
    """A group of items: fit_many + predict_many in this task (one process)."""
    t0 = time.time()
    from prophet_batch import fit_many, predict_many

    _quiet()
    models = fit_many(pdf[['unique_id', 'ds', 'y']], n_jobs=1)
    fcs = predict_many(models, periods=H, seed=0, history_uncertainty='analytic', columns=BANDS)
    t1 = time.time()
    return pd.concat([_rows(str(sid), fcs[sid].tail(H).to_numpy().T, float(m.params['lp__'][0, 0]), t0, t1)
                      for sid, m in models.items()], ignore_index=True)


def _to_result(method: str, out: pd.DataFrame, seconds: float, workers: int) -> Result:
    out = out.sort_values(['unique_id', 'step'])
    ids = list(dict.fromkeys(out['unique_id']))
    arr = {k: out[k].to_numpy().reshape(len(ids), H) for k in BANDS}
    lp = out.groupby('unique_id', sort=True)['lp'].first().loc[ids].to_numpy()
    return Result(method, workers, ids, arr['yhat'], arr['yhat_lower'], arr['yhat_upper'], lp, seconds, 0.0, len(ids))


def task_stats(out: pd.DataFrame, execute_s: float, cores: int) -> dict:
    """Parallelism actually used, from the per-task records (a task = one item for stock, one group for batch)."""
    tasks = out.drop_duplicates(['host', 'pid', 't0', 't1'])[['host', 'pid', 't0', 't1']]
    busy = float((tasks['t1'] - tasks['t0']).sum())
    events = sorted([(t, 1) for t in tasks['t0']] + [(t, -1) for t in tasks['t1']])
    level = peak = 0
    for _, step in events:
        level += step
        peak = max(peak, level)
    return {'tasks': len(tasks), 'hosts': int(tasks['host'].nunique()),
            'processes': int(tasks[['host', 'pid']].drop_duplicates().shape[0]), 'max_concurrent': peak,
            'task_seconds_sum': busy, 'task_seconds_median': float((tasks['t1'] - tasks['t0']).median()),
            'core_utilisation': busy / (execute_s * cores) if execute_s > 0 and cores else None,
            'per_host_tasks': {str(h): int(n) for h, n in tasks['host'].value_counts().items()}}


def _copy(spark, src: str, dst: str) -> None:
    """Copy a file between the local disk and a Hadoop filesystem URI (gs://, file://) through Spark."""
    jvm = spark._jvm
    conf = spark._jsc.hadoopConfiguration()
    src_path, dst_path = jvm.org.apache.hadoop.fs.Path(src), jvm.org.apache.hadoop.fs.Path(dst)
    if dst.startswith('gs://'):
        dst_path.getFileSystem(conf).copyFromLocalFile(False, True, src_path, dst_path)
    else:
        src_path.getFileSystem(conf).copyToLocalFile(False, src_path, dst_path, True)


def main(argv: list[str] | None = None) -> int:
    marks = {'script_start': time.time()}
    from pyspark.sql import SparkSession

    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--data', required=True, help='directory (URI) with sales_train_evaluation.csv and calendar.csv')
    p.add_argument('--out', required=True, help='directory (URI) for the results')
    p.add_argument('--method', choices=('batch', 'stock'), required=True)
    p.add_argument('--groups', type=int, default=0, help='item groups for batch (default: 4 per executor core)')
    p.add_argument('--run-id', default=None, help='label for the output files (e.g. the batch id)')
    p.add_argument('--wait', type=int, default=600, help='seconds to wait for executors (default 600)')
    p.add_argument('--n', type=int, default=0, help='first n items only, for smoke tests (default: all)')
    a = p.parse_args(argv)

    spark = SparkSession.builder.appName(f'walmart-{a.method}').getOrCreate()
    sc = spark.sparkContext
    spark.conf.set('spark.sql.execution.arrow.pyspark.enabled', 'true')
    marks['session_ready'] = time.time()

    local_mode = sc.master.startswith('local')
    expected = int(sc.getConf().get('spark.executor.instances', '0') or 0)
    tracker = sc._jsc.sc().statusTracker()
    seen = []
    while not local_mode:
        seen.append(len(tracker.getExecutorInfos()) - 1)  # minus the driver
        if (expected and seen[-1] >= expected) or time.time() - marks['session_ready'] > a.wait:
            break
        time.sleep(2)
    executors = 0 if local_mode else len(tracker.getExecutorInfos()) - 1
    marks['executors_ready'] = time.time()
    if not local_mode and executors == 0:
        raise SystemExit('no executors registered; stopping')
    cores = sc.defaultParallelism
    print(f'master {sc.master}; executors {executors}/{expected}; parallelism {cores}', flush=True)

    local = Path(tempfile.mkdtemp())
    for name in ('sales_train_evaluation.csv', 'calendar.csv'):
        _copy(spark, f"{a.data.rstrip('/')}/{name}", f'file://{local / name}')
    train, test = data.split(data.load_items(local))
    if a.n:
        train, test = train.iloc[:a.n], test.iloc[:a.n]
    long_df = data.to_long(train)
    groups = a.groups or 4 * cores
    # Spark's adaptive execution would merge the post-shuffle partitions of this small (in bytes) data into one or two
    # tasks, serialising the work; keep one partition per 1/4 core for both methods.
    spark.conf.set('spark.sql.adaptive.coalescePartitions.enabled', 'false')
    spark.conf.set('spark.sql.shuffle.partitions', str(4 * cores))
    long_df['group'] = [zlib.crc32(s.encode()) % groups for s in long_df['unique_id']]
    sdf = spark.createDataFrame(long_df).cache()
    sdf.count()
    marks['load_done'] = time.time()

    print(f'{a.method}: {len(train):,} items; groups {groups if a.method == "batch" else "-"}', flush=True)
    marks['execute_start'] = time.time()
    if a.method == 'batch':
        out = sdf.groupBy('group').applyInPandas(batch_group, OUT_SCHEMA).toPandas()
    else:
        out = sdf.groupBy('unique_id').applyInPandas(stock_item, OUT_SCHEMA).toPandas()
    marks['execute_end'] = time.time()
    execute_s = marks['execute_end'] - marks['execute_start']
    print(f'{a.method}: execute {execute_s:.1f} s', flush=True)

    r = _to_result(a.method, out, execute_s, cores)
    acc = evaluate(r, train, test)
    run_id = a.run_id or f'{a.method}-{time.strftime("%Y%m%d-%H%M%S")}'
    marks['write_start'] = time.time()
    record = {
        'run_id': run_id, 'method': a.method, 'n': len(train), 'groups': groups if a.method == 'batch' else None,
        'marks': marks, 'spark': {'version': spark.version, 'master': sc.master, 'default_parallelism': cores,
                                  'executors': executors, 'executors_expected': expected,
                                  'executors_seen': seen[-5:], 'conf': {k: v for k, v in sc.getConf().getAll()
                                                                        if k.startswith(('spark.executor',
                                                                                         'spark.driver.cores',
                                                                                         'spark.dynamicAllocation'))},
                                  'shuffle_partitions': spark.conf.get('spark.sql.shuffle.partitions'),
                                  'coalesce_partitions': spark.conf.get(
                                      'spark.sql.adaptive.coalescePartitions.enabled')},
        'machine': machine_info(), 'tasks': task_stats(out, execute_s, cores),
        'accuracy': acc['summary'], 'per_series': {k: v.tolist() for k, v in acc['per_series'].items()},
        'lp': r.lp.tolist(), 'ids': r.ids,
    }
    (local / f'{run_id}.json').write_text(json.dumps(record, indent=1, default=str))
    np.savez_compressed(local / f'{run_id}.npz', ids=np.array(r.ids), yhat=r.yhat, lower=r.lower, upper=r.upper)
    for suffix in ('json', 'npz'):
        _copy(spark, f'file://{local / f"{run_id}.{suffix}"}', f"{a.out.rstrip('/')}/{run_id}.{suffix}")
    end = local / f'{run_id}.end.json'  # results written: the rest until the platform's end time is shutdown
    end.write_text(json.dumps({'write_end': time.time()}))
    _copy(spark, f'file://{end}', f"{a.out.rstrip('/')}/{end.name}")
    print(json.dumps({'run_id': run_id, 'execute_s': execute_s, 'tasks': record['tasks']['tasks'],
                      'hosts': record['tasks']['hosts'], 'max_concurrent': record['tasks']['max_concurrent'],
                      'wape': acc['summary']['wape']}), flush=True)
    spark.stop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
