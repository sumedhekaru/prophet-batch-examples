"""One public dataset on Spark: one method per run, every phase timed, every task recorded (protocol of track F5).

    spark-submit spark_main.py --data DIR --out DIR --dataset m4_daily --method batch|stock [--groups N] [--n N]

  batch  series hashed into --groups groups; groupBy(group).applyInPandas runs fit_many + predict_many on each group
         (many series per task; history_uncertainty='analytic', only the interval columns returned)
  stock  groupBy(series).applyInPandas runs Prophet().fit + predict on each series (one series per task)
Default Prophet() on the dataset's train split, forecast history + the holdout (as run.py). The job itself (phases,
task records, outputs) is examples_core/spark.py; this module loads the data: the dataset's files under --data, laid
out as data.py downloads them (m5/, m4/, tourism/), read on the driver with data.load.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from examples_core.spark import Loaded, fetch, run_job

from . import data

FILES = {'m5': ['m5/sales_train_evaluation.csv', 'm5/calendar.csv'],
         'tourism': ['tourism/tourism_monthly_dataset.tsf']}


def _files(name: str) -> list[str]:
    if name.startswith('m4_'):
        stem = data._M4[name[3:]][0]
        return [f'm4/{stem}-train.csv', f'm4/{stem}-test.csv', 'm4/M4-info.csv']
    return FILES[data.SOURCE[name]]


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument('--dataset', choices=data.NAMES, required=True)
    p.add_argument('--n', type=int, default=None, help='random sample of n series, as run.py (default: all)')


def _load(spark: Any, a: argparse.Namespace, local: Path) -> Loaded:
    fetch(spark, a.data, _files(a.dataset), local)
    ds = data.load(a.dataset, a.n, data_dir=local)
    return Loaded(ds.train.copy(), ds.train_wide, ds.test_wide, ds.horizon, ds.freq, ds.season,
                  {'dataset': ds.name})


def main(argv: list[str] | None = None) -> int:
    return run_job(argv, 'public', __doc__, _args, _load)


if __name__ == '__main__':
    sys.exit(main())
