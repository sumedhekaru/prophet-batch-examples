"""The use case on Spark: one method per run, every phase timed, every task recorded (benchmark protocol, track F5).

    spark-submit spark_main.py --data DIR --out DIR --method batch|stock [--groups N] [--run-id ID] [--n N]

  batch  items hashed into --groups groups; groupBy(group).applyInPandas runs fit_many + predict_many on each group
         (many series per task; history_uncertainty='analytic', only the interval columns returned)
  stock  groupBy(item).applyInPandas runs Prophet().fit + predict on each item (one series per task)
Both use all 1,437 items and forecast history + 28 days (as run.py). The job itself (phases, task records, outputs)
is examples_core/spark.py; this module loads the data: sales_train_evaluation.csv and calendar.csv from --data.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from examples_core.spark import Loaded, fetch, run_job

from . import data
from .run import SEASON


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument('--n', type=int, default=0, help='first n items only, for smoke tests (default: all)')


def _load(spark: Any, a: argparse.Namespace, local: Path) -> Loaded:
    fetch(spark, a.data, ['sales_train_evaluation.csv', 'calendar.csv'], local)
    train, test = data.split(data.load_items(local))
    if a.n:
        train, test = train.iloc[:a.n], test.iloc[:a.n]
    return Loaded(data.to_long(train), train, test, data.HORIZON, 'D', SEASON)


def main(argv: list[str] | None = None) -> int:
    return run_job(argv, 'walmart', __doc__, _args, _load)


if __name__ == '__main__':
    sys.exit(main())
