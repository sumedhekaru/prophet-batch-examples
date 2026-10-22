"""Holdout accuracy metrics, per series (arrays over the h test days).

WAPE      sum|y - f| / sum|y|, pooled over series by summing both parts
sMAPE     M4 definition, in percent: 200/h * sum |y - f| / (|y| + |f|); a day with y = f = 0 counts as 0
MASE      M4 definition: mean|y - f| / mean|x_t - x_{t-m}| over the training series x, seasonal period m (7 here);
          NaN when that scale is 0 (constant training series)
coverage  share of test days with lower <= y <= upper (80% intervals by default)

Same definitions as the parallel-prophet benchmarks, so numbers are comparable.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

Array = npt.ArrayLike


def wape_parts(y: Array, f: Array) -> tuple[float, float]:
    """(sum |y - f|, sum |y|): sum each over series for a pooled WAPE."""
    y, f = np.asarray(y, float), np.asarray(f, float)
    return float(np.sum(np.abs(y - f))), float(np.sum(np.abs(y)))


def smape(y: Array, f: Array) -> float:
    y, f = np.asarray(y, float), np.asarray(f, float)
    den = np.abs(y) + np.abs(f)
    terms = np.divide(np.abs(y - f), den, out=np.zeros_like(den), where=den > 0)
    return float(200 * terms.mean())


def mase(y: Array, f: Array, train: Array, m: int) -> float:
    y, f, x = np.asarray(y, float), np.asarray(f, float), np.asarray(train, float)
    if len(x) <= m:
        return np.nan
    scale = np.mean(np.abs(x[m:] - x[:-m]))
    return float(np.mean(np.abs(y - f)) / scale) if scale > 0 else np.nan


def coverage(y: Array, lower: Array, upper: Array) -> float:
    y = np.asarray(y, float)
    return float(np.mean((np.asarray(lower, float) <= y) & (y <= np.asarray(upper, float))))
