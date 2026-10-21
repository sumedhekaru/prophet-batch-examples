"""Forecast plots from a run's saved forecasts (results/runs/*.npz)."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Reference categorical palette, slots 1-2 (validated light-mode pair); ink for actuals and history.
BATCH, STOCK = '#2a78d6', '#eb6834'
INK, INK_2, GRID = '#0b0b0b', '#52514e', '#e4e3df'


def load_forecasts(npz: Path) -> tuple[list[str], pd.DatetimeIndex, dict[str, dict[str, np.ndarray]]]:
    """(item ids, test dates, {method_workers: {yhat, lower, upper}}) from a run's npz."""
    z = np.load(npz, allow_pickle=False)
    methods: dict[str, dict[str, np.ndarray]] = {}
    for key in z.files:
        if key.endswith(('_yhat', '_lower', '_upper')):
            name, band = key.rsplit('_', 1)
            methods.setdefault(name, {})[band] = z[key]
    return [str(i) for i in z['ids']], pd.DatetimeIndex(z['test_ds']), methods


def _pick(methods: dict, prefix: str) -> str:
    """The method key with this prefix and the most workers (e.g. stock_pool_10)."""
    keys = [k for k in methods if k.startswith(prefix)]
    return max(keys, key=lambda k: int(k.rsplit('_', 1)[1]))


def plot_items(npz: Path, wide: pd.DataFrame, items: list[str], history_days: int = 56,
               batch: str = 'batch_analytic', stock: str = 'stock_pool') -> plt.Figure:
    """One panel per item: the last history days, the held-out actuals, and both forecasts with 80% intervals."""
    ids, test_ds, methods = load_forecasts(npz)
    pos = {s: i for i, s in enumerate(ids)}
    b, s = methods[_pick(methods, batch)], methods[_pick(methods, stock)]
    cols = 2
    rows = -(-len(items) // cols)
    fig, axes = plt.subplots(rows, cols, figsize=(12, 3.2 * rows), squeeze=False, sharex=True)
    for ax, item in zip(axes.flat, items):
        i, y = pos[item], wide.loc[item]
        hist = y[y.index < test_ds[0]].tail(history_days)
        ax.plot(hist.index, hist.to_numpy(), color=INK_2, lw=1.5, label='history')
        ax.plot(test_ds, y.loc[test_ds].to_numpy(), color=INK, lw=2, label='actual (held out)')
        for f, color, ls, label in ((s, STOCK, '--', 'stock Prophet'), (b, BATCH, '-', 'prophet-batch')):
            ax.fill_between(test_ds, f['lower'][i], f['upper'][i], color=color, alpha=0.12, lw=0)
            ax.plot(test_ds, f['yhat'][i], color=color, lw=2, ls=ls, label=f'{label} (80% interval shaded)')
        ax.axvline(test_ds[0], color=GRID, lw=1)
        ax.set_title(item, loc='left', fontsize=10, color=INK)
        ax.grid(axis='y', color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        for side in ('top', 'right'):
            ax.spines[side].set_visible(False)
        ax.spines['left'].set_color(GRID)
        ax.spines['bottom'].set_color(GRID)
        ax.tick_params(colors=INK_2, labelsize=8)
        ax.set_ylabel('units / day', fontsize=8, color=INK_2)
    for ax in list(axes.flat)[len(items):]:
        ax.set_visible(False)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper center', ncol=4, frameon=False, fontsize=9)
    fig.autofmt_xdate()
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return fig
