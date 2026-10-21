"""The use case on Spark (Dataproc Serverless): stock Prophet one item per task vs prophet-batch per group of items.

    spark-submit spark_main.py --data gs://BUCKET/data/m5 --out gs://BUCKET/results [--groups 16]

  batch  items hashed into --groups groups; groupBy(group).applyInPandas: fit_many + predict_many on each group, so
         every task fits many series at once (history_uncertainty='analytic', only the interval columns returned)
  stock  groupBy(item).applyInPandas: Prophet().fit + predict for each item, the usual Spark pattern; on a random
         sample of --stock-n items (it is slow), timed and extrapolated; accuracy compared on that sample
The driver first waits for the executors (and stops if none arrive), then runs batch, then stock.
Both forecast history + 28 days, as in run.py; times are the wall time of each Spark job (data shuffled in, results
collected). Forecasts are seeded per series, so prophet-batch's match a local run's whatever the grouping.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
import zlib
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from . import data
from .forecast import Result
from .run import evaluate, machine_info, paired

H = data.HORIZON
OUT_SCHEMA = ('unique_id string, step int, yhat double, yhat_lower double, yhat_upper double, lp double, '
              'fit_s double, predict_s double')
BANDS = ['yhat', 'yhat_lower', 'yhat_upper']


def _quiet() -> None:
    import logging

    logging.getLogger('cmdstanpy').disabled = True
    logging.getLogger('prophet').setLevel(logging.WARNING)


def _rows(sid: str, bands: np.ndarray, lp: float, fit_s: float, predict_s: float) -> pd.DataFrame:
    return pd.DataFrame({'unique_id': sid, 'step': np.arange(H, dtype=np.int32), 'yhat': bands[0],
                         'yhat_lower': bands[1], 'yhat_upper': bands[2], 'lp': lp, 'fit_s': fit_s,
                         'predict_s': predict_s})


def stock_item(pdf: pd.DataFrame) -> pd.DataFrame:
    """One item: Prophet().fit + predict (seeded like run.py's stock side)."""
    from prophet import Prophet

    _quiet()
    sid = str(pdf['unique_id'].iloc[0])
    t0 = time.perf_counter()
    m = Prophet().fit(pdf[['ds', 'y']].sort_values('ds'))
    t1 = time.perf_counter()
    np.random.seed(zlib.crc32(sid.encode()))
    fc = m.predict(m.make_future_dataframe(H)).tail(H)
    t2 = time.perf_counter()
    return _rows(sid, fc[BANDS].to_numpy().T, float(m.params['lp__'][0, 0]), t1 - t0, t2 - t1)


def batch_group(pdf: pd.DataFrame) -> pd.DataFrame:
    """A group of items: fit_many + predict_many in this task (one process)."""
    from prophet_batch import fit_many, predict_many

    _quiet()
    t0 = time.perf_counter()
    models = fit_many(pdf[['unique_id', 'ds', 'y']], n_jobs=1)
    t1 = time.perf_counter()
    fcs = predict_many(models, periods=H, seed=0, history_uncertainty='analytic', columns=BANDS)
    t2 = time.perf_counter()
    return pd.concat([_rows(str(sid), fcs[sid].tail(H).to_numpy().T, float(m.params['lp__'][0, 0]),
                            t1 - t0, t2 - t1) for sid, m in models.items()], ignore_index=True)


def _to_result(method: str, out: pd.DataFrame, seconds: float, workers: int) -> Result:
    out = out.sort_values(['unique_id', 'step'])
    ids = list(dict.fromkeys(out['unique_id']))
    arr = {k: out[k].to_numpy().reshape(len(ids), H) for k in BANDS}
    lp = out.groupby('unique_id', sort=True)['lp'].first().loc[ids].to_numpy()
    return Result(method, workers, ids, arr['yhat'], arr['yhat_lower'], arr['yhat_upper'], lp, seconds, 0.0,
                  len(ids), {'task_fit_s': float(out.groupby('unique_id')['fit_s'].first().sum()),
                             'task_predict_s': float(out.groupby('unique_id')['predict_s'].first().sum())})


def _subset(r: Result, ids: list[str]) -> Result:
    pos = [r.ids.index(s) for s in ids]
    return Result(r.method, r.workers, list(ids), r.yhat[pos], r.lower[pos], r.upper[pos], r.lp[pos], r.fit_s,
                  r.predict_s, len(ids), r.extra)


def _copy(spark, src: str, dst: str) -> None:
    """Copy a file between the local disk and gs:// through Spark's Hadoop filesystem (GCS connector)."""
    jvm = spark._jvm
    conf = spark._jsc.hadoopConfiguration()
    src_path, dst_path = jvm.org.apache.hadoop.fs.Path(src), jvm.org.apache.hadoop.fs.Path(dst)
    remote = dst_path if dst.startswith('gs://') else src_path
    fs = remote.getFileSystem(conf)
    if dst.startswith('gs://'):
        fs.copyFromLocalFile(False, True, src_path, dst_path)
    else:
        fs.copyToLocalFile(False, src_path, dst_path, True)


def main(argv: list[str] | None = None) -> int:
    from pyspark.sql import SparkSession

    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--data', required=True, help='directory with sales_train_evaluation.csv and calendar.csv')
    p.add_argument('--out', required=True, help='directory for the results')
    p.add_argument('--groups', type=int, default=16, help='item groups for prophet-batch (default 16)')
    p.add_argument('--stock-n', type=int, default=300, help='items for the stock run (default 300)')
    p.add_argument('--wait', type=int, default=600, help='seconds to wait for executors (default 600)')
    a = p.parse_args(argv)

    spark = SparkSession.builder.appName('walmart-grocery-forecasting').getOrCreate()
    spark.conf.set('spark.sql.execution.arrow.pyspark.enabled', 'true')
    expected = int(spark.conf.get('spark.executor.instances', '1'))
    cores = expected * int(spark.conf.get('spark.executor.cores', '1'))
    tracker = spark.sparkContext._jsc.sc().statusTracker()
    t0 = time.perf_counter()
    while not spark.sparkContext.master.startswith('local'):  # local mode: tasks run in the driver
        up = len(tracker.getExecutorInfos()) - 1  # minus the driver
        if up >= expected or time.perf_counter() - t0 > a.wait:
            break
        time.sleep(5)
    up = len(tracker.getExecutorInfos()) - 1 if not spark.sparkContext.master.startswith('local') else 1
    print(f'executors up {up}/{expected} after {time.perf_counter() - t0:.0f} s', flush=True)
    if up == 0:
        raise SystemExit('no executors started; stopping')
    local = Path(tempfile.mkdtemp())
    for name in ('sales_train_evaluation.csv', 'calendar.csv'):
        _copy(spark, f"{a.data.rstrip('/')}/{name}", f'file://{local / name}')
    train, test = data.split(data.load_items(local))
    long_df = data.to_long(train)
    long_df['group'] = [zlib.crc32(s.encode()) % a.groups for s in long_df['unique_id']]
    sdf = spark.createDataFrame(long_df).cache()
    sdf.count()
    print(f'{len(train):,} items; {a.groups} groups', flush=True)

    rng = np.random.default_rng(0)
    sample = sorted(str(x) for x in rng.choice(list(train.index), size=min(a.stock_n, len(train)), replace=False))
    results = []
    for method, run, n_items in (
            ('spark_batch_per_group',
             lambda: sdf.groupBy('group').applyInPandas(batch_group, OUT_SCHEMA), len(train)),
            ('spark_stock_per_item',
             lambda: sdf.filter(sdf.unique_id.isin(sample)).groupBy('unique_id')
                        .applyInPandas(stock_item, OUT_SCHEMA), len(sample))):
        print(f'{method}: started ({n_items} items)', flush=True)
        t0 = time.perf_counter()
        out = run().toPandas()
        seconds = time.perf_counter() - t0
        results.append(_to_result(method, out, seconds, cores))
        print(f'{method}: {seconds:.1f} s for {n_items} items', flush=True)

    batch, stock = results
    stock_full_s = stock.total_s * len(train) / len(sample)
    ids = sample
    sub = train.loc[ids], test.loc[ids]
    acc = {r.method: evaluate(_subset(r, ids), *sub) for r in results}
    gain = batch.lp[[batch.ids.index(s) for s in ids]] - stock.lp[[stock.ids.index(s) for s in ids]]
    report = {
        'machine': {**machine_info(), 'spark': spark.version,
                    'executor_instances': spark.conf.get('spark.executor.instances', None),
                    'executor_cores': spark.conf.get('spark.executor.cores', None)},
        'n': len(train), 'stock_n': len(sample), 'groups': a.groups, 'executors_up': up,
        'seconds': {r.method: r.total_s for r in results}, 'stock_seconds_extrapolated': stock_full_s,
        'task_seconds': {r.method: r.extra for r in results},
        'accuracy': {k: v['summary'] for k, v in acc.items()},
        'mase_vs_stock': paired(acc[stock.method]['per_series']['mase'], acc[batch.method]['per_series']['mase']),
        'lp_ge_stan_share': float(np.mean(gain >= -1e-6)),
    }
    s, b, d = acc[stock.method]['summary'], acc[batch.method]['summary'], report['mase_vs_stock']
    md = '\n'.join([
        f"# walmart_grocery_forecasting on Spark {spark.version}: {len(train):,} M5 FOODS items, 28-day holdout", '',
        f"{report['machine']['timestamp']} · executors {report['machine']['executor_instances']} × "
        f"{report['machine']['executor_cores']} cores · prophet {report['machine']['versions']['prophet']} · "
        f"prophet-batch {report['machine']['commits']['prophet-batch']} · {a.groups} groups", '',
        f"| method | wall s, all {len(train):,} items | vs stock |", '|---|---:|---:|',
        f"| stock, one item per task (timed on {len(sample)}, extrapolated) | {stock_full_s:.1f} | 1.0× |",
        f"| prophet-batch, fit_many per group | {batch.total_s:.1f} | {stock_full_s / batch.total_s:.1f}× |", '',
        f"Accuracy on the {len(sample)} stock items: WAPE {s['wape']:.4f} / {b['wape']:.4f}, MASE {s['mase']:.4f} / "
        f"{b['mase']:.4f}, 80% coverage {s['coverage']:.3f} / {b['coverage']:.3f} (stock / prophet-batch); "
        f"Δ MASE {d['mean']:+.4f} ± {2 * d['se']:.4f}; log posterior ≥ Stan's on "
        f"{100 * report['lp_ge_stan_share']:.1f}% of them.", ''])
    print(md, flush=True)
    stem = f"spark-default-{len(train)}-{datetime.now():%Y%m%d-%H%M%S}"
    (local / f'{stem}.json').write_text(json.dumps(report, indent=1, default=str))
    (local / f'{stem}.md').write_text(md)
    np.savez_compressed(local / f'{stem}.npz', ids=np.array(batch.ids), stock_ids=np.array(stock.ids),
                        **{f'{r.method}_{k}': getattr(r, k) for r in results for k in ('yhat', 'lower', 'upper')})
    for suffix in ('json', 'md', 'npz'):
        _copy(spark, f'file://{local / f"{stem}.{suffix}"}', f"{a.out.rstrip('/')}/{stem}.{suffix}")
    spark.stop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
