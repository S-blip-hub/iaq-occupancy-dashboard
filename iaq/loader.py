"""Load paired indoor/outdoor exports from testo 160 IAQ loggers.

The loggers export one row per reading with a matched timestamp and six
channels per sensor: CO2 (ppm), air temperature (deg C), pressure (mbar),
relative humidity (%RH), dew point (deg C td) and absolute humidity (g/m3).
This module turns that export into a tidy, time-indexed DataFrame with short
snake_case column names.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

UNIT_TO_NAME = {
    "ppm": "co2_ppm",
    "°C": "temp_c",
    "mbar": "pressure_mbar",
    "%RH": "rh_pct",
    "°C td": "dewpoint_c",
    "g/m³": "abs_humidity_gm3",
}

_COL_RE = re.compile(r"^\s*(indoor|outdoor)\s*\[(.+?)\]\s*$", re.IGNORECASE)


def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename 'indoor [ppm]' style headers to 'in_co2_ppm', 'out_temp_c', ..."""
    renamed = {}
    for col in df.columns:
        m = _COL_RE.match(str(col))
        if not m:
            continue
        side, unit = m.group(1).lower(), m.group(2).strip()
        if unit not in UNIT_TO_NAME:
            raise ValueError(f"unknown unit '{unit}' in column '{col}'")
        renamed[col] = ("in_" if side == "indoor" else "out_") + UNIT_TO_NAME[unit]
    return df.rename(columns=renamed)


def load_export(path: str | Path, sheet: str | int = "master sheet", dayfirst: bool = True) -> pd.DataFrame:
    """Read an .xlsx or .csv export and return a clean, sorted frame.

    * the timestamp column is detected by name ('timestamp' in the header)
    * duplicate timestamps are dropped (first reading kept)
    * readings outside physical ranges are set to NaN
    """
    path = Path(path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        raw = pd.read_excel(path, sheet_name=sheet)
    else:
        raw = pd.read_csv(path)

    ts_cols = [c for c in raw.columns if "timestamp" in str(c).lower()]
    if not ts_cols:
        raise ValueError("no timestamp column found")
    ts = pd.to_datetime(raw[ts_cols[0]], dayfirst=dayfirst, errors="coerce")

    df = normalise_columns(raw.drop(columns=ts_cols))
    df.index = ts
    df.index.name = "timestamp"
    df = df[df.index.notna()].sort_index()
    df = df[~df.index.duplicated(keep="first")]
    return apply_range_checks(df)


# Plausible ranges for these sensors in a naturally ventilated Indian building.
VALID_RANGES = {
    "co2_ppm": (250, 5000),
    "temp_c": (5, 50),
    "pressure_mbar": (950, 1050),
    "rh_pct": (0, 100),
    "dewpoint_c": (-10, 35),
    "abs_humidity_gm3": (0, 40),
}


def apply_range_checks(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        key = col.split("_", 1)[1] if col.startswith(("in_", "out_")) else col
        if key in VALID_RANGES:
            lo, hi = VALID_RANGES[key]
            out.loc[(out[col] < lo) | (out[col] > hi), col] = float("nan")
    return out
