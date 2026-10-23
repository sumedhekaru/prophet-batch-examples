"""Figures for the write-up, built from the run records (results/runs/), so anyone can regenerate them.

    uv run python -m examples_core.figures --out figures/ \\
        --walmart walmart_grocery_forecasting/results/runs/local-bench-<stamp> \\
        --public public_datasets/results/runs/local-bench-<stamp> --small public_datasets/results/runs/local-bench-<stamp> \\
        --scaling public_datasets/results/runs/scaling-local-<...>.json \\
        --workers public_datasets/results/runs/scaling-workers-local-<...>.json \\
        --spark walmart=<dataproc-bench dir> --spark item×store=<dataproc-bench dir>/m5_item_store \\
        --stream streaming_csv/results/runs/<1M run>.json

Every argument is optional; a figure whose records are not given is skipped. PNGs at 2× for the web.
Colours: the reference categorical palette, slots 1–3 (blue = prophet-batch forecast_many, orange = stock Prophet,
aqua = the two-step path / default intervals), validated all-pairs for colour-vision deficiency; aqua is below 3:1
contrast on white, so every series is also labelled directly.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402
import numpy as np  # noqa: E402

BLUE, ORANGE, AQUA = '#2a78d6', '#eb6834', '#1baf7a'
INK, INK_2, MUTED, GRID, SURFACE = '#0b0b0b', '#52514e', '#8a8984', '#e4e3df', '#ffffff'
GREYS = ['#c9c8c2', '#a9a8a1', '#dad9d4']  # overhead phases (recessive), execute is blue
NAMES = {'m5_item_store': 'M5 item × store', 'm4_daily': 'M4 Daily', 'm5_item': 'M5 item', 'm4_weekly': 'M4 Weekly',
         'm4_hourly': 'M4 Hourly', 'tourism_monthly': 'Tourism Monthly', 'default': 'Walmart 1,437 items'}

plt.rcParams.update({
    'font.family': 'sans-serif', 'font.size': 10, 'axes.edgecolor': GRID, 'axes.linewidth': 1,
    'axes.labelcolor': INK_2, 'xtick.color': INK_2, 'ytick.color': INK_2, 'axes.grid': True, 'grid.color': GRID,
    'grid.linewidth': 0.8, 'axes.axisbelow': True, 'axes.spines.top': False, 'axes.spines.right': False,
    'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE, 'savefig.dpi': 200, 'legend.frameon': False,
    'axes.titlesize': 11, 'axes.titleweight': 'bold', 'axes.titlecolor': INK, 'axes.titlelocation': 'left'})


def _runs(directory: Path) -> list[dict]:
    """Every run record (json with rows) in a REPS directory, with its npz path."""
    out = []
    for f in sorted(directory.glob('*.json')):
        rec = json.loads(f.read_text(encoding='utf-8'))
        if 'rows' in rec:
            rec['_npz'] = f.with_suffix('.npz')
            out.append(rec)
    return out


def _group(rec: dict) -> str:
    return rec['machine'].get('dataset') or rec['machine'].get('model') or 'default'


def _median_total(runs: list[dict], method: str, workers: int | None = None) -> float:
    vals = [r['total_s'] for rec in runs for r in rec['rows']
            if r['method'] == method and (workers is None or r['workers'] == workers)]
    return float(np.median(vals))


def _speedups(runs: list[dict]) -> dict[str, tuple[float, float]]:
    """{group: (median speed-up forecast_many analytic, forecast_many sampled)} vs the stock pool, per repetition."""
    by: dict[str, list[dict]] = {}
    for rec in runs:
        by.setdefault(_group(rec), []).append(rec)
    out = {}
    for g, recs in by.items():
        ratios = {m: [] for m in ('forecast_many_analytic', 'forecast_many_sampled')}
        for rec in recs:
            rows = {r['method']: r for r in rec['rows'] if r['method'] != 'stock_serial'
                    and r['workers'] == max(x['workers'] for x in rec['rows'])}
            for m in ratios:
                ratios[m].append(rows['stock_pool']['total_s'] / rows[m]['total_s'])
        out[g] = (float(np.median(ratios['forecast_many_analytic'])), float(np.median(ratios['forecast_many_sampled'])))
    return out


def _label_bar(ax, y: float, x: float, text: str) -> None:
    ax.text(x, y, f'  {text}', va='center', ha='left', color=INK, fontsize=9)


def hero(dirs: list[Path], out: Path) -> None:
    """Speed-up vs a full stock process pool, per dataset: analytic history intervals and the default."""
    runs = [rec for d in dirs for rec in _runs(d) if _group(rec) in NAMES]
    sp = _speedups(runs)
    order = sorted(sp, key=lambda g: sp[g][0])
    y = np.arange(len(order))
    h = 0.36
    fig, ax = plt.subplots(figsize=(7.5, 0.55 * len(order) + 1.6))
    ax.barh(y + h / 2, [sp[g][0] for g in order], height=h, color=BLUE, label="history_uncertainty='analytic'")
    ax.barh(y - h / 2, [sp[g][1] for g in order], height=h, color=AQUA, label='default (history intervals sampled)')
    for i, g in enumerate(order):
        _label_bar(ax, y[i] + h / 2, sp[g][0], f'{sp[g][0]:.1f}×')
        _label_bar(ax, y[i] - h / 2, sp[g][1], f'{sp[g][1]:.1f}×')
    ax.set_yticks(y, [NAMES[g] for g in order])
    ax.tick_params(axis='y', length=0)
    ax.grid(axis='y', visible=False)
    ax.set_xlabel('times faster than a 10-process stock Prophet pool (fit + forecast, median)')
    ax.set_xlim(0, max(v[0] for v in sp.values()) * 1.15)
    ax.set_title('prophet-batch vs stock Prophet on the same 10 cores (Apple M4)')
    ax.legend(loc='lower right', fontsize=9)
    fig.tight_layout()
    fig.savefig(out / 'fig1-speedup.png')
    plt.close(fig)


def accuracy(dirs: list[Path], out: Path) -> None:
    """Per-series MASE, stock vs prophet-batch (first repetition of each dataset): on the diagonal."""
    first: dict[str, dict] = {}
    for d in dirs:
        for rec in _runs(d):
            first.setdefault(_group(rec), rec)
    groups = [g for g in NAMES if g in first and g != 'default']
    cols = 3
    rows = int(np.ceil(len(groups) / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(3.2 * cols, 3.1 * rows), squeeze=False)
    for ax, g in zip(axes.flat, groups):
        ps = first[g]['per_series']
        a, b = np.array(ps['stock_pool_10']['mase']), np.array(ps['forecast_many_analytic_10']['mase'])
        ok = np.isfinite(a) & np.isfinite(b) & (a > 0) & (b > 0)
        a, b = a[ok], b[ok]
        lo, hi = min(a.min(), b.min()), max(a.max(), b.max())
        ax.plot([lo, hi], [lo, hi], color=MUTED, linewidth=1, zorder=1)
        ax.scatter(a, b, s=4, color=BLUE, alpha=0.35, linewidths=0, rasterized=True, zorder=2)
        ax.set_xscale('log')
        ax.set_yscale('log')
        for axis in (ax.xaxis, ax.yaxis):
            axis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        d = next(r for r in first[g]['rows'] if r['method'] == 'forecast_many_analytic').get('mase_vs_stock', {})
        ax.set_title(f'{NAMES[g]} ({len(a):,})', fontsize=10)
        ax.text(0.03, 0.97, f"Δ MASE {d.get('mean', 0):+.4f} ± {2 * d.get('se', 0):.4f}", transform=ax.transAxes,
                va='top', fontsize=8.5, color=INK_2)
    for ax in axes.flat[len(groups):]:
        ax.set_visible(False)
    for ax in axes[-1]:
        ax.set_xlabel('MASE, stock Prophet')
    for ax in axes[:, 0]:
        ax.set_ylabel('MASE, prophet-batch')
    fig.suptitle('Same accuracy: one dot per series, on the diagonal (log scales)', x=0.01, ha='left',
                 fontweight='bold', color=INK)
    fig.tight_layout()
    fig.savefig(out / 'fig2-accuracy.png')
    plt.close(fig)


def fit_quality(dirs: list[Path], out: Path) -> None:
    """Log-posterior gain over Stan per series (prophet-batch − stock), first repetition of each dataset."""
    first: dict[str, dict] = {}
    for d in dirs:
        for rec in _runs(d):
            first.setdefault(_group(rec), rec)
    groups = [g for g in NAMES if g in first and g != 'default']
    fig, axes = plt.subplots(len(groups), 1, figsize=(7.5, 0.95 * len(groups) + 1.0), sharex=True, squeeze=False)
    total = above = 0
    for ax, g in zip(axes[:, 0], groups):
        z = np.load(first[g]['_npz'])
        gain = z['forecast_many_analytic_10_lp'] - z['stock_pool_10_lp']
        total, above = total + len(gain), above + int(np.sum(gain >= -1e-6))
        pos = np.clip(gain, 1e-4, None)
        ax.hist(pos, bins=np.logspace(-4, 3, 57), color=BLUE)
        ax.set_xscale('log')
        ax.set_yticks([])
        ax.grid(axis='y', visible=False)
        ax.text(0.0, 0.5, f'{NAMES[g]}  ', transform=ax.transAxes, ha='right', va='center', color=INK, fontsize=9)
        ax.text(1.0, 0.85, f'median {np.median(gain):.2g}', transform=ax.transAxes, ha='right', va='top',
                color=INK_2, fontsize=8.5)
    axes[-1, 0].set_xlabel('log posterior of prophet-batch minus Stan\'s, per series (≥ 0 = at least as good a fit)')
    fig.suptitle(f'A better fit by Prophet\'s own measure: ≥ Stan on {above:,} of {total:,} series', x=0.01,
                 ha='left', fontweight='bold', color=INK)
    fig.tight_layout()
    fig.subplots_adjust(left=0.2)
    fig.savefig(out / 'fig3-fit-quality.png')
    plt.close(fig)


def _end_label(ax, x, y, text) -> None:
    ax.annotate(text, (x, y), xytext=(6, 0), textcoords='offset points', va='center', fontsize=9, color=INK)


def scaling(path: Path, out: Path) -> None:
    """Seconds vs number of series, log–log; medians per point."""
    rec = json.loads(path.read_text(encoding='utf-8'))
    ns = sorted({p['n'] for p in rec['points']})
    med = {m: [np.median([p['seconds'][m]['total_s'] for p in rec['points'] if p['n'] == n]) for n in ns]
           for m in ('stock_pool', 'batch_analytic', 'forecast_many_analytic')}
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    for m, color, label in (('stock_pool', ORANGE, 'stock Prophet, 10-process pool'),
                            ('batch_analytic', AQUA, 'fit_many + predict_many'),
                            ('forecast_many_analytic', BLUE, 'forecast_many')):
        ax.plot(ns, med[m], color=color, linewidth=2, marker='o', markersize=6, markeredgecolor=SURFACE,
                markeredgewidth=1.5, label=label)
        _end_label(ax, ns[-1], med[m][-1], f'{med[m][-1]:.0f} s')
    ratio = [np.median([p['seconds']['stock_pool']['total_s'] / p['seconds']['forecast_many_analytic']['total_s']
                        for p in rec['points'] if p['n'] == n]) for n in ns]
    for n, r, f in zip(ns, ratio, med['forecast_many_analytic']):
        ax.annotate(f'{r:.1f}×', (n, f), xytext=(0, -14), textcoords='offset points', ha='center',
                    fontsize=8.5, color=INK_2)
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel('number of series (M5 item × store, nested samples)')
    ax.set_ylabel('seconds, fit + forecast')
    ax.set_xlim(ns[0] * 0.7, ns[-1] * 2.2)
    ax.set_ylim(min(med['forecast_many_analytic']) * 0.5, None)
    ax.set_title('Time grows linearly; the gain grows with the number of series')
    ax.legend(loc='upper left', fontsize=9)
    fig.tight_layout()
    fig.savefig(out / 'fig5-scaling.png')
    plt.close(fig)


def workers(path: Path, out: Path) -> None:
    """Seconds vs worker count at a fixed number of series."""
    rec = json.loads(path.read_text(encoding='utf-8'))
    ws = sorted({p['workers'] for p in rec['points']})
    n = rec['points'][0]['n']
    get = {m: [np.median([p['seconds'][m]['total_s'] for p in rec['points'] if p['workers'] == w]) for w in ws]
           for m in ('stock_pool', 'forecast_many_analytic')}
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for m, color, label in (('stock_pool', ORANGE, 'stock Prophet, process pool'),
                            ('forecast_many_analytic', BLUE, 'prophet-batch forecast_many')):
        ax.plot(ws, get[m], color=color, linewidth=2, marker='o', markersize=6, markeredgecolor=SURFACE,
                markeredgewidth=1.5, label=label)
    for w, s, f in zip(ws, get['stock_pool'], get['forecast_many_analytic']):
        ax.annotate(f'{s / f:.0f}×', (w, f), xytext=(0, 9), textcoords='offset points', ha='center', fontsize=8.5,
                    color=INK_2)
    ax.set_xticks(ws)
    ax.set_xlabel('worker processes (Apple M4: 4 performance + 6 efficiency cores)')
    ax.set_ylabel('seconds, fit + forecast')
    ax.set_ylim(0, max(get['stock_pool']) * 1.08)
    ax.set_title(f'The gain is in the work, not the cores: {get["stock_pool"][0] / get["forecast_many_analytic"][0]:.0f}× '
                 f'on one core ({n:,} series)')
    ax.legend(loc='upper right', fontsize=9)
    fig.tight_layout()
    fig.savefig(out / 'fig5b-workers.png')
    plt.close(fig)


def spark(dirs: dict[str, Path], out: Path) -> None:
    """Spark batch phases (medians), stacked: platform setup, load + warm-up, execute, write + shutdown."""
    from examples_core.spark_summary import load

    segments = [('platform setup', ('provision', 'driver_start', 'executors'), GREYS[0]),
                ('load + warm-up', ('load', 'warmup'), GREYS[1]),
                ('execute (fit + forecast)', ('execute',), BLUE),
                ('write + shutdown', ('post', 'shutdown'), GREYS[2])]
    fig, axes = plt.subplots(len(dirs), 1, figsize=(8, 1.9 * len(dirs) + 1.2), squeeze=False)
    for ax, (label, d) in zip(axes[:, 0], dirs.items()):
        runs = load(d)
        bars = []
        for method, name in (('stock', 'stock Prophet'), ('batch', 'prophet-batch')):
            rs = [r for r in runs if r['method'] == method]
            if rs:
                bars.append((name, [float(np.median([sum(r['phases'][p] or 0 for p in ps) for r in rs]))
                                    for _, ps, _ in segments]))
        y = np.arange(len(bars))[::-1]
        for i, (name, vals) in enumerate(bars):
            left = 0.0
            for (seg, _, color), v in zip(segments, vals):
                ax.barh(y[i], v, left=left, height=0.6, color=color, edgecolor=SURFACE, linewidth=2,
                        label=seg if ax is axes[0, 0] and i == 0 else None)
                left += v
            ax.text(left, y[i], f'  {left / 60:.1f} min', va='center', fontsize=9, color=INK)
        total = [sum(v) for _, v in bars]
        ax.set_yticks(y, [b[0] for b in bars], fontsize=9)
        ax.tick_params(axis='y', length=0)
        ax.grid(axis='y', visible=False)
        ax.set_xlim(0, max(total) * 1.18)
        e2e = [np.median([r['phases']['end_to_end'] for r in runs if r['method'] == m]) for m in ('stock', 'batch')]
        gain = f'{e2e[0] / e2e[1]:.1f}× end to end' if len(total) == 2 and all(np.isfinite(e2e)) else ''
        ax.set_title(f'{label}: {gain}', fontsize=10)
    axes[-1, 0].set_xlabel('seconds per Spark batch (Dataproc Serverless, 2 executors × 4 cores; median of 3)')
    fig.suptitle('On Spark, setup is fixed: the gain grows with the job', x=0.01, ha='left', fontweight='bold',
                 color=INK)
    fig.legend(loc='lower center', fontsize=8.5, ncol=4, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(out / 'fig4-spark-phases.png')
    plt.close(fig)


def stream(path: Path, out: Path) -> None:
    """Memory over time for a streaming run: the main process and all worker processes together."""
    rec = json.loads(path.read_text(encoding='utf-8'))
    tl = rec['memory']['timeline']
    t = np.array([row[0] for row in tl]) / 60
    main_gb = np.array([row[1] for row in tl])
    w = np.array([(row[0], row[2]) for row in tl if len(row) > 2 and row[2] is not None], dtype=float)
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.plot(t, main_gb, color=BLUE, linewidth=1.5, label='main process (reader, writer, batches in flight)')
    _end_label(ax, t[-1], main_gb[-1], 'main process')
    if len(w):
        ax.plot(w[:, 0] / 60, w[:, 1], color=AQUA, linewidth=1.5, label='all 10 workers together')
        _end_label(ax, w[-1, 0] / 60, w[-1, 1], 'all workers')
    ax.set_ylim(0, max(2.0, float(np.nanmax(main_gb)) * 1.3, float(np.nanmax(w[:, 1])) * 1.3 if len(w) else 0))
    ax.set_xlim(0, t[-1] * 1.18)
    ax.set_xlabel('minutes')
    ax.set_ylabel('memory, GB')
    ax.set_title(f"{rec['series']:,} series from a {rec['input_mb'] / 1e3:.1f} GB file: memory stays bounded")
    ax.legend(loc='upper left', fontsize=9)
    fig.tight_layout()
    fig.savefig(out / 'fig6-stream-memory.png')
    plt.close(fig)


def pattern(out: Path) -> None:
    """The streaming pattern (streaming_csv): reader → bounded queue → Pool.forecast_many → bounded queue → writer."""
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 46)
    ax.axis('off')
    IO, Q = '#f1f0ec', '#ffffff'

    def box(x, y, w, h, title, body, face, edge=GRID, title_color=INK, lw=1.2):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.4,rounding_size=1.2', facecolor=face,
                                    edgecolor=edge, linewidth=lw))
        ax.text(x + w / 2, y + h - 2.2, title, ha='center', va='top', fontsize=10, fontweight='bold', color=title_color)
        ax.text(x + w / 2, y + h - 6.2, body, ha='center', va='top', fontsize=8.3, color=INK_2, linespacing=1.35)

    def arrow(x0, x1, y=27):
        ax.add_patch(FancyArrowPatch((x0, y), (x1, y), arrowstyle='-|>', mutation_scale=14, color=INK_2,
                                     linewidth=1.4))

    box(0.5, 16, 11.5, 22, 'Your data', 'any size:\nCSV, Parquet,\na database,\nSpark\npartitions', IO)
    box(15, 16, 11.5, 22, 'Reader', 'thread:\nwhole series\nper batch\n(e.g. 1,000)', IO)
    box(29.5, 21, 6, 12, 'queue', '≤ 2\nbatches', Q, edge=MUTED)
    box(38.5, 12, 23, 30, 'Pool.forecast_many', 'prophet-batch fits and\nforecasts each batch', '#eaf2fc', edge=BLUE,
        lw=1.6)
    for i in range(5):
        ax.add_patch(FancyBboxPatch((40.6 + i * 4.2, 18.5), 2.9, 5.0, boxstyle='round,pad=0.2,rounding_size=0.6',
                                    facecolor=BLUE, edgecolor=SURFACE, linewidth=1))
    ax.text(50, 16.0, 'worker processes, kept for the\nwhole run: ≈ 0.14 GB each', ha='center', va='top', fontsize=7.8,
            color=INK_2, linespacing=1.3)
    box(64.5, 21, 6, 12, 'queue', '≤ 2\nbatches', Q, edge=MUTED)
    box(73.5, 16, 11.5, 22, 'Writer', 'thread:\none file per\nbatch, written\nthen renamed', IO)
    box(88, 16, 11.5, 22, 'Your output', 'forecasts,\nin the same\nstore or\nanother', IO)
    for x0, x1 in ((12.6, 14.6), (27.1, 29.1), (36.1, 38.1), (62.1, 64.1), (71.1, 73.1), (85.6, 87.6)):
        arrow(x0, x1)
    ax.text(50, 7.5, 'Read, forecast and write overlap. At most ≈ 5 batches exist at once, so memory is set by the batch '
            'size, not the file:', ha='center', fontsize=9, color=INK)
    ax.text(50, 3.6, '1,000,072 series (7.4 GB gzip) in 33 minutes on a laptop, main process ≤ 1.04 GB. '
            'A part that exists is skipped, so a stopped run resumes.', ha='center', fontsize=9, color=INK_2)
    ax.set_title('Forecasting a catalogue of any size with bounded memory', loc='left', fontsize=12, fontweight='bold',
                 color=INK, pad=6)
    fig.tight_layout()
    fig.savefig(out / 'fig7-streaming-pattern.png')
    plt.close(fig)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--out', type=Path, default=Path('figures'))
    p.add_argument('--walmart', type=Path, action='append', default=[])
    p.add_argument('--public', type=Path, action='append', default=[])
    p.add_argument('--small', type=Path, action='append', default=[])
    p.add_argument('--scaling', type=Path)
    p.add_argument('--workers', type=Path)
    p.add_argument('--spark', action='append', default=[], help='label=directory (a Spark benchmark directory)')
    p.add_argument('--stream', type=Path)
    p.add_argument('--pattern', action='store_true', help='the streaming-pattern diagram')
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    datasets = a.public + a.small
    if datasets or a.walmart:
        hero(a.walmart + datasets, a.out)
    if datasets:
        accuracy(datasets, a.out)
        fit_quality(datasets, a.out)
    if a.scaling:
        scaling(a.scaling, a.out)
    if a.workers:
        workers(a.workers, a.out)
    if a.spark:
        spark({label: Path(d) for label, d in (x.split('=', 1) for x in a.spark)}, a.out)
    if a.stream:
        stream(a.stream, a.out)
    if a.pattern:
        pattern(a.out)
    print(f'figures in {a.out}: {sorted(f.name for f in a.out.glob("*.png"))}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
