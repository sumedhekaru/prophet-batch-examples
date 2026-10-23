# Windows results on prophet-batch 0.1.2 (PyPI): PARTIAL, paused

**Status (2026-10-23 08:5x):** runs a and b are done and clean. Run c was stopped partway through at the user's request
(the laptop was needed). Its timings are partly invalid because of connected standby (see below). d and e were not run.

| run | command | status | start–end | result folder |
|---|---|---|---|---|
| a | `REPS=3 sh walmart_grocery_forecasting/envs/local/run.sh` | done, exit 0 | 10-22 17:36–20:52 (3 h 15 min) | `local-bench-20261022-173708/` |
| b | `REPS=1 DATASETS="m4_weekly m4_hourly tourism_monthly" sh public_datasets/envs/local/run.sh` | done, exit 0 | 10-22 20:52–21:04 (12 min) | `local-bench-20261022-205229/` |
| c | `REPS=3 DATASETS="m5_item m4_daily" sh public_datasets/envs/local/run.sh` | stopped (killed), no summary.md | 10-22 21:04 – 10-23 08:5x | `_aborted/local-bench-20261022-210440/` (do not use) |
| d | streaming x1/x2/x4/x8 + check.py | not run | – | – |
| e | `REPS=1 DATASETS="m5_item_store" sh public_datasets/envs/local/run.sh` | not run | – | – |

## To resume

1. On main power: activate High performance (add it with `powercfg -duplicatescheme 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c`
   if only Balanced exists), and set **all three** AC timeouts to 0 (never):
   `powercfg /change standby-timeout-ac 0`, `hibernate-timeout-ac 0`, **`monitor-timeout-ac 0`**. In Git Bash, set
   `MSYS_NO_PATHCONV=1` first. Restore everything afterwards.
2. `git checkout results/windows-0.1.2`, check that examples is still at 6d2f22b (or rerun a and b if main moved), `uv sync`,
   and rerun the verify line.
3. Rerun **c in full** (≈ 4.5–5 h), then d, then e. a and b don't need rerunning. Copy the new folders here and
   delete `_aborted/` (or keep it as evidence) when adding the clean c.

## Machine and setup

- 12th Gen Intel(R) Core(TM) i7-1260P, 16 logical CPUs, 34.04 GB RAM, Windows 10 22H2 (19045), Python 3.12.10 (pyenv).
- Verify line: `0.1.2 (PyPI) | 12th Gen Intel(R) Core(TM) i7-1260P | 34.042929152`.
- examples 6d2f22b. `uv sync` moved prophet-batch from 0.1.1 to 0.1.2. PROPHET_BATCH_LOCAL and PROPHET_BATCH_COMMIT were not set.
- Power: on AC. Only Balanced existed, so I added High performance (31cb3906-…) and activated it. Its AC standby and hibernate
  timeouts were already 0. Its display timeout on AC was 600 s and was **not** changed (the cause of the problem below).
  Restored afterwards: Balanced active, added plan deleted.
- Apps left open: Chrome, VS Code, Antigravity, DBeaver, Excel, Word, RingCentral, RustDesk, GitHub Desktop, Notepad++,
  Java (jp2launcher, jucheck). Idle CPU 23–53% (one reading of 84%). Top users: RustDesk (≈ 1.4 cores), then RingCentral.

## Results so far

- **a:** header `prophet-batch 0.1.2 (PyPI)`. default, events and events_snap: bit-identical in every run yes, min share
  1.0000, fallbacks 0. All 9 records have forecast_many vs batch (n_jobs=16) bit-identical: True. Median total vs stock
  pool: batch analytic 16 workers 10.3× / 10.4× / 9.6×; forecast_many analytic 15.8× / 13.2× / 12.6×.
- **b:** header `prophet-batch 0.1.2 (PyPI)`. All three datasets: bit-identical yes, min share 1.0000, fallbacks 0;
  forecast_many checks True in every record. forecast_many analytic vs stock pool: m4_weekly 6.6×, m4_hourly 4.6×,
  tourism_monthly 3.8×. On these small datasets, batch analytic with 1 worker is faster than with 16 (19.3 vs 30.1 s, 19.4 vs
  23.8 s, 11.3 vs 19.9 s).

## What went wrong in c (confirmed from the Windows System log)

At 23:08 the display turned off (Kernel-Power 506, reason SC_MONITORPOWER) and the laptop went into connected standby
(S0 low power idle; the only standby state this machine has). It stayed there, apart from brief wake-ups about hourly, until a
keypress at 08:24 (Kernel-Power 507, reason Input Keyboard). Setting standby and hibernate to 0 does not prevent this.

- m5_item rep 1 (21:04–21:38): normal.
- m4_daily rep 1 (21:38–23:15): its last step (batch n_jobs=1) overlapped the start of standby. I can't verify whether it
  was affected (no clean m4_daily rep to compare).
- m5_item rep 2 (23:15–08:25): batch n_jobs=1 predict 19,186.5 s sampled / 12,734.9 s analytic, against 580.3 / 54.6 s in
  rep 1. Its 16-worker steps look normal.
- m4_daily rep 2 was running when c was stopped. It left no record.

No errors or tracebacks in the a or b logs. The c log ends with 40 "Optimization terminated abnormally. Falling back to
Newton." lines and a RuntimeError traceback ("Error during optimization!" from cmdstanpy in a stock_pool worker, m4_daily rep 2).
The Stan output files named in it are stamped 08:55:49–51, the minute c was killed, and nothing like it appears earlier
in the log. So it is most likely a side effect of stopping the run, not a benchmark failure (unconfirmed).
