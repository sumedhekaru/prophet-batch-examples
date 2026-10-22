"""Fit + forecast every series with stock Prophet and with prophet-batch, timed (shared by every use case).

Every method does what a user does: fit the model (a use case's ModelSpec) on the training rows, then forecast the
history plus the next `horizon` steps (`make_future_dataframe(horizon, freq=spec.freq)`, with the regressor values
joined), so the timings include history intervals. Accuracy uses the last `horizon` rows.

  stock_serial  Prophet().fit + predict per series in one process (on a sample: it is slow; extrapolated)
  stock_pool    the same per series in a process pool (spawn, `workers` processes)
  batch         prophet_batch.fit_many + predict_many with n_jobs=`workers`; history intervals sampled like stock
                (history_uncertainty=True) and exact closed form ('analytic'), both from the same fit
Stock forecasts seed numpy with crc32(item id) before each predict; prophet-batch uses seed=0 (per-series streams).
"""

from __future__ import annotations

import logging
import multiprocessing
import time
import zlib
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np
import pandas as pd
from prophet import Prophet


class ModelSpec(Protocol):
    """What the runners need from a use case's model definition (picklable: it goes to worker processes).

    freq: the series' frequency (pandas alias, e.g. 'D', '7D', 'h', 'MS'); regressors: extra regressor columns (their
    values come from with_regressors); kwargs(): Prophet() arguments shared by every series; called with a series id,
    returns a fresh unfitted model for it.
    """

    freq: str
    regressors: list[str]

    def __call__(self, series_id: object = None) -> Prophet: ...

    def kwargs(self) -> dict: ...

    def with_regressors(self, df: pd.DataFrame) -> pd.DataFrame: ...

BANDS = ['yhat', 'yhat_lower', 'yhat_upper']


@dataclass
class Result:
    """One method's forecasts of the test days (arrays in item order) and its timings."""

    method: str
    workers: int
    ids: list[str]
    yhat: np.ndarray  # (n, horizon)
    lower: np.ndarray
    upper: np.ndarray
    lp: np.ndarray  # (n,) log posterior of each fit (Stan's lp__ or prophet-batch's)
    fit_s: float
    predict_s: float
    timed_n: int  # series the timing covers (fewer than len(ids) when extrapolated)
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def total_s(self) -> float:
        return self.fit_s + self.predict_s

    def seconds_for(self, n: int) -> float:
        """Fit + forecast seconds for n series (extrapolated linearly when only a sample was timed)."""
        return self.total_s * n / self.timed_n


def _quiet() -> None:
    for name in ('cmdstanpy', 'prophet'):
        logging.getLogger(name).setLevel(logging.WARNING)
    logging.getLogger('cmdstanpy').disabled = True


def _stock_one(args: tuple[str, pd.DataFrame, int, ModelSpec]) -> tuple[str, np.ndarray, float, float, float]:
    sid, train, horizon, spec = args
    _quiet()
    t0 = time.perf_counter()
    m = spec(sid).fit(train)
    t1 = time.perf_counter()
    np.random.seed(zlib.crc32(sid.encode()))
    fc = m.predict(spec.with_regressors(m.make_future_dataframe(horizon, freq=spec.freq))).tail(horizon)
    t2 = time.perf_counter()
    bands = fc[['yhat', 'yhat_lower', 'yhat_upper']].to_numpy().T
    return sid, bands, float(m.params['lp__'][0, 0]), t1 - t0, t2 - t1


def _stock_result(method: str, workers: int, out: list, fit_s: float, predict_s: float) -> Result:
    ids, bands, lp, _, _ = zip(*out)
    bands = np.array(bands)
    return Result(method, workers, list(ids), bands[:, 0], bands[:, 1], bands[:, 2], np.array(lp),
                  fit_s, predict_s, len(ids))


def run_stock_serial(series: dict[str, pd.DataFrame], horizon: int, spec: ModelSpec) -> Result:
    out = [_stock_one((sid, df, horizon, spec)) for sid, df in series.items()]
    return _stock_result('stock_serial', 1, out, sum(o[3] for o in out), sum(o[4] for o in out))


def run_stock_pool(series: dict[str, pd.DataFrame], horizon: int, spec: ModelSpec, workers: int) -> Result:
    """Wall time of the whole pool; split into fit / predict by the workers' summed shares."""
    t0 = time.perf_counter()
    ctx = multiprocessing.get_context('spawn')
    with ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as pool:
        out = list(pool.map(_stock_one, [(sid, df, horizon, spec) for sid, df in series.items()], chunksize=4))
    wall = time.perf_counter() - t0
    fit_share = sum(o[3] for o in out) / sum(o[3] + o[4] for o in out)
    return _stock_result('stock_pool', workers, out, wall * fit_share, wall * (1 - fit_share))


class _Fallbacks(logging.Handler):
    """Collects fit_many's per-series fallback reasons (its debug log lines; in-process fits only)."""

    def __init__(self) -> None:
        super().__init__(logging.DEBUG)
        self.reasons: dict[str, str] = {}

    def emit(self, record: logging.LogRecord) -> None:
        if str(record.msg).startswith('Series %r falls back to Prophet.fit'):
            sid, reason = record.args  # type: ignore[misc]
            self.reasons[str(sid)] = str(reason)


def run_batch(long_df: pd.DataFrame, horizon: int, spec: ModelSpec, workers: int, seed: int = 0) -> list[Result]:
    """One fit_many, then predict_many once per history-interval mode; one Result per mode.

    Used as the prophet-batch README says: Prophet arguments shared by all series go to fit_many directly; regressors
    need make_model, and their future values go in `futures`. Only the interval columns are kept (`columns=`), as the
    stock workers return only those too; full frames with 30 holidays would be 2.3 GB.
    """
    from prophet_batch import fit_many, predict_many

    log = logging.getLogger('prophet_batch')
    handler, level = _Fallbacks(), log.level
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)
    try:
        t0 = time.perf_counter()
        if spec.regressors:
            models = fit_many(long_df, make_model=spec, n_jobs=workers)
        else:
            models = fit_many(long_df, n_jobs=workers, **spec.kwargs())
        fit_s = time.perf_counter() - t0
    finally:
        log.removeHandler(handler)
        log.setLevel(level)
    ids = list(models)
    lp = np.array([float(models[sid].params['lp__'][0, 0]) for sid in ids])
    results = []
    for mode in (True, 'analytic'):
        t0 = time.perf_counter()
        if spec.regressors:
            futures = {sid: spec.with_regressors(m.make_future_dataframe(horizon, freq=spec.freq))
                       for sid, m in models.items()}
            fcs = predict_many(models, futures=futures, seed=seed, n_jobs=workers, history_uncertainty=mode,
                               columns=BANDS)
        else:
            fcs = predict_many(models, periods=horizon, freq=spec.freq, seed=seed, n_jobs=workers,
                               history_uncertainty=mode, columns=BANDS)
        predict_s = time.perf_counter() - t0
        bands = np.array([fcs[sid][BANDS].tail(horizon).to_numpy().T
                          for sid in ids])
        name = 'batch_sampled' if mode is True else 'batch_analytic'
        extra = {'fallbacks': handler.reasons} if workers == 1 else {}
        results.append(Result(name, workers, [str(s) for s in ids], bands[:, 0], bands[:, 1], bands[:, 2], lp,
                              fit_s, predict_s, len(ids), extra))
    return results
