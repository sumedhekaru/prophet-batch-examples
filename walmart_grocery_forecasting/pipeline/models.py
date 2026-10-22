"""Model variants, identical for stock Prophet and prophet-batch.

  default      Prophet()
  events       Prophet(holidays=M5 calendar events): event_name_1 and event_name_2, each on its day only
  events_snap  events plus the SNAP days of the three states (snap_CA, snap_TX, snap_WI) as additive regressors;
               the items are summed over stores in all three states, so each flag gets its own coefficient

SNAP days are scheduled in advance, so their test-day values are known at forecast time (as in the M5 competition).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from prophet import Prophet

VARIANTS = ('default', 'events', 'events_snap')
SNAP = ['snap_CA', 'snap_TX', 'snap_WI']


def load_calendar(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(regressors: ds + SNAP flags for every day incl. the test days, holidays: Prophet's holiday frame)."""
    cal = pd.read_csv(data_dir / 'calendar.csv', parse_dates=['date']).rename(columns={'date': 'ds'})
    holidays = pd.concat([cal[['ds', c]].dropna().rename(columns={c: 'holiday'})
                          for c in ('event_name_1', 'event_name_2')], ignore_index=True)
    holidays['lower_window'], holidays['upper_window'] = 0, 0
    return cal[['ds', *SNAP]].astype({c: float for c in SNAP}), holidays


class ModelSpec:
    """A picklable `make_model(series_id)` for one variant, plus the regressor values it needs."""

    freq = 'D'

    def __init__(self, variant: str, data_dir: Path) -> None:
        if variant not in VARIANTS:
            raise ValueError(f'unknown model variant {variant!r}; choose from {VARIANTS}')
        self.variant = variant
        regressors, holidays = load_calendar(data_dir)
        self.holidays = holidays if variant != 'default' else None
        self.regressors = SNAP if variant == 'events_snap' else []
        self.calendar = regressors if self.regressors else None

    def kwargs(self) -> dict:
        """Prophet() arguments shared by every series."""
        return {} if self.holidays is None else {'holidays': self.holidays}

    def __call__(self, series_id: object = None) -> Prophet:
        m = Prophet(**self.kwargs())
        for c in self.regressors:
            m.add_regressor(c)
        return m

    def with_regressors(self, df: pd.DataFrame) -> pd.DataFrame:
        """df with this variant's regressor columns joined on ds (unchanged when there are none)."""
        if self.calendar is None:
            return df
        out = df.merge(self.calendar, on='ds', how='left')
        assert not out[self.regressors].isna().any().any(), 'regressor values missing for some dates'
        return out
