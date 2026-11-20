"""Indoor environmental quality indicators and a CO2-based occupancy proxy.

The dataset has no occupancy counter, so occupancy is inferred from CO2:
people exhale CO2, so when the indoor concentration rises well above the
outdoor level, or climbs quickly, the space is very likely occupied. This is a
standard proxy in building-science studies, not a head count.
"""

from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd

# Indicative CO2 bands widely used for classroom/office ventilation feedback.
CO2_BANDS = [(0, 800, "good"), (800, 1200, "moderate"), (1200, np.inf, "poor")]

# Thermal comfort band for naturally ventilated rooms (simple fixed band used
# for screening; adaptive comfort models would widen it in hot months).
COMFORT_TEMP_C = (20.0, 30.0)
COMFORT_RH_PCT = (30.0, 70.0)


def co2_band(ppm: pd.Series) -> pd.Series:
    labels = pd.Series(index=ppm.index, dtype="object")
    for lo, hi, name in CO2_BANDS:
        labels[(ppm >= lo) & (ppm < hi)] = name
    return labels


def occupancy_proxy(df: pd.DataFrame, delta_ppm: float = 60.0, rise_ppm_per_h: float = 40.0) -> pd.Series:
    """Return a boolean Series: True where the room is likely occupied.

    A reading counts as occupied when indoor CO2 exceeds outdoor CO2 by more
    than ``delta_ppm``, or when indoor CO2 is rising faster than
    ``rise_ppm_per_h``. A 3-reading rolling median removes single spikes.
    """
    excess = df["in_co2_ppm"] - df["out_co2_ppm"]
    step_h = df.index.to_series().diff().dt.total_seconds() / 3600.0
    rate = df["in_co2_ppm"].diff() / step_h.replace(0, np.nan)
    occ = (excess > delta_ppm) | (rate > rise_ppm_per_h)
    smoothed = occ.astype(float).rolling(3, center=True, min_periods=1).median()
    return smoothed >= 0.5


def summary(df: pd.DataFrame) -> Dict[str, float]:
    """Headline numbers for the whole monitoring period."""
    occ = occupancy_proxy(df)
    in_comfort = df["in_temp_c"].between(*COMFORT_TEMP_C) & df["in_rh_pct"].between(*COMFORT_RH_PCT)
    bands = co2_band(df["in_co2_ppm"]).value_counts(normalize=True)
    return {
        "readings": int(len(df)),
        "days": int(df.index.normalize().nunique()),
        "indoor_co2_mean_ppm": float(df["in_co2_ppm"].mean()),
        "indoor_co2_p95_ppm": float(df["in_co2_ppm"].quantile(0.95)),
        "indoor_co2_max_ppm": float(df["in_co2_ppm"].max()),
        "share_co2_good": float(bands.get("good", 0.0)),
        "share_co2_moderate": float(bands.get("moderate", 0.0)),
        "share_co2_poor": float(bands.get("poor", 0.0)),
        "indoor_temp_mean_c": float(df["in_temp_c"].mean()),
        "indoor_minus_outdoor_temp_mean_c": float((df["in_temp_c"] - df["out_temp_c"]).mean()),
        "share_in_comfort_band": float(in_comfort.mean()),
        "share_likely_occupied": float(occ.mean()),
        "co2_when_occupied_mean_ppm": float(df.loc[occ, "in_co2_ppm"].mean()) if occ.any() else float("nan"),
        "co2_when_unoccupied_mean_ppm": float(df.loc[~occ, "in_co2_ppm"].mean()) if (~occ).any() else float("nan"),
    }


def hourly_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Mean indoor CO2, temperature, RH and occupancy share by hour of day."""
    occ = occupancy_proxy(df).astype(float)
    g = df.assign(occupied=occ).groupby(df.index.hour)
    return pd.DataFrame({
        "in_co2_ppm": g["in_co2_ppm"].mean(),
        "out_co2_ppm": g["out_co2_ppm"].mean(),
        "in_temp_c": g["in_temp_c"].mean(),
        "out_temp_c": g["out_temp_c"].mean(),
        "in_rh_pct": g["in_rh_pct"].mean(),
        "occupied_share": g["occupied"].mean(),
    }).rename_axis("hour")


def daily_summary(df: pd.DataFrame) -> pd.DataFrame:
    occ = occupancy_proxy(df).astype(float)
    d = df.assign(occupied=occ)
    g = d.groupby(d.index.normalize())
    out = pd.DataFrame({
        "in_co2_mean": g["in_co2_ppm"].mean(),
        "in_co2_max": g["in_co2_ppm"].max(),
        "out_co2_mean": g["out_co2_ppm"].mean(),
        "in_temp_mean": g["in_temp_c"].mean(),
        "in_temp_max": g["in_temp_c"].max(),
        "out_temp_mean": g["out_temp_c"].mean(),
        "out_temp_max": g["out_temp_c"].max(),
        "in_rh_mean": g["in_rh_pct"].mean(),
        "occupied_hours": g["occupied"].sum() * 0.25,
    })
    out.index.name = "date"
    return out.round(2)
