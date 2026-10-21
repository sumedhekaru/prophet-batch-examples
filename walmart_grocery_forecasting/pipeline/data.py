"""M5 (Walmart) data for this use case: download, verify, load FOODS items.

    uv run python -m walmart_grocery_forecasting.pipeline.data             # download into data/m5/
    uv run python -m walmart_grocery_forecasting.pipeline.data --from DIR  # reuse an m5.zip already in DIR

The archive is the M5 data as packaged by Nixtla (github.com/Nixtla/m5-forecasts, no login needed), pinned by
SHA-256. A file with a wrong checksum is never used. Only the two CSVs this use case reads are extracted.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

URL = "https://github.com/Nixtla/m5-forecasts/raw/main/datasets/m5.zip"
SHA256 = "cc704ba15d6802f8262e6ec7d4c6041e4ad6366a94365e8c84f721e450eed774"
MEMBERS = ["sales_train_evaluation.csv", "calendar.csv"]
DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "m5"

HORIZON = 28  # the M5 evaluation horizon: the last 28 days are held out
CATEGORY = "FOODS"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch(data_dir: Path = DATA_DIR, source: Path | None = None) -> Path:
    """Put a verified m5.zip in data_dir (copied from source if given, else downloaded) and extract MEMBERS."""
    zip_path = data_dir / "m5.zip"
    data_dir.mkdir(parents=True, exist_ok=True)
    if zip_path.exists() and sha256(zip_path) == SHA256:
        print(f"{zip_path}: ok")
    else:
        tmp = zip_path.with_name("m5.zip.part")
        if source is not None:
            print(f"copying {source / 'm5.zip'}")
            shutil.copyfile(source / "m5.zip", tmp)
        else:
            print(f"downloading {URL}")
            with urllib.request.urlopen(URL) as r, open(tmp, "wb") as f:
                shutil.copyfileobj(r, f, 1 << 20)
        got = sha256(tmp)
        if got != SHA256:
            tmp.unlink()
            raise RuntimeError(f"m5.zip: checksum {got} != pinned {SHA256}")
        tmp.replace(zip_path)
        print(f"{zip_path}: verified")
    with zipfile.ZipFile(zip_path) as z:
        for name in MEMBERS:
            if not (data_dir / name).exists():
                z.extract(name, data_dir)
                print(f"extracted {name}")
    return data_dir


def load_items(data_dir: Path = DATA_DIR, category: str = CATEGORY) -> pd.DataFrame:
    """Daily unit sales of each item in the category, summed over the 10 stores.

    Returns
    -------
    Wide float DataFrame: one row per item_id (sorted), one column per date (1,941 days).
    """
    sales = pd.read_csv(data_dir / "sales_train_evaluation.csv")
    sales = sales[sales["cat_id"] == category]
    day_cols = [c for c in sales.columns if c.startswith("d_")]
    wide = sales.groupby("item_id")[day_cols].sum().astype(float)
    # Calendar rows are in day order: d_1 is the first date.
    dates = pd.to_datetime(pd.read_csv(data_dir / "calendar.csv", usecols=["date"])["date"])
    wide.columns = pd.DatetimeIndex(dates.iloc[[int(c[2:]) - 1 for c in day_cols]].to_numpy(), name="ds")
    return wide.sort_index()


def split(wide: pd.DataFrame, horizon: int = HORIZON) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(train, test): all days but the last `horizon`, and the last `horizon`."""
    return wide.iloc[:, :-horizon], wide.iloc[:, -horizon:]


def to_long(wide: pd.DataFrame) -> pd.DataFrame:
    """Long format for Prophet and prophet-batch: columns unique_id, ds, y (sorted by id, then date)."""
    return pd.DataFrame({
        "unique_id": np.repeat(wide.index.to_numpy(), wide.shape[1]),
        "ds": np.tile(wide.columns.to_numpy(), len(wide)),
        "y": wide.to_numpy().ravel(),
    })


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--from", dest="source", type=Path, help="directory holding an m5.zip to copy instead of downloading")
    p.add_argument("--data-dir", type=Path, default=DATA_DIR, help=f"where to put the data (default {DATA_DIR})")
    a = p.parse_args()
    fetch(a.data_dir, a.source)
    train, test = split(load_items(a.data_dir))
    print(f"{CATEGORY} items: {len(train):,} series x {train.shape[1] + test.shape[1]:,} days "
          f"(train {train.shape[1]:,}, test {test.shape[1]}): {train.columns[0].date()} to {test.columns[-1].date()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
