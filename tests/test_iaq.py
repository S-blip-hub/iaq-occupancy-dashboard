import numpy as np
import pandas as pd
import pytest

from iaq.loader import apply_range_checks, normalise_columns
from iaq.metrics import co2_band, daily_summary, hourly_profile, occupancy_proxy, summary
from iaq.store import load_queries, run_all, to_sqlite


def make_frame(days=2):
    idx = pd.date_range("2023-10-01", periods=days * 96, freq="15min", name="timestamp")
    hour = idx.hour.to_numpy()
    occupied = (hour >= 9) & (hour < 18)
    in_co2 = np.where(occupied, 650.0, 400.0)
    return pd.DataFrame({
        "out_co2_ppm": 410.0, "out_temp_c": 28.0, "out_rh_pct": 70.0,
        "in_co2_ppm": in_co2, "in_temp_c": 29.0, "in_rh_pct": 60.0,
    }, index=idx), occupied


def test_normalise_columns():
    df = pd.DataFrame(columns=["indoor [ppm]", "outdoor [°C]", "indoor [%RH]", "outdoor [g/m³]"])
    assert list(normalise_columns(df).columns) == ["in_co2_ppm", "out_temp_c", "in_rh_pct", "out_abs_humidity_gm3"]


def test_range_checks_remove_impossible_values():
    df = pd.DataFrame({"in_co2_ppm": [400, 50, 9000], "in_rh_pct": [50, 120, -1]})
    out = apply_range_checks(df)
    assert out["in_co2_ppm"].isna().tolist() == [False, True, True]
    assert out["in_rh_pct"].isna().tolist() == [False, True, True]


def test_co2_bands():
    s = pd.Series([500, 900, 1500])
    assert co2_band(s).tolist() == ["good", "moderate", "poor"]


def test_occupancy_proxy_matches_schedule():
    df, occupied = make_frame()
    occ = occupancy_proxy(df).to_numpy()
    assert (occ == occupied).mean() > 0.95


def test_summary_and_profiles():
    df, _ = make_frame()
    s = summary(df)
    assert s["readings"] == len(df) and s["days"] == 2
    assert s["co2_when_occupied_mean_ppm"] > s["co2_when_unoccupied_mean_ppm"]
    prof = hourly_profile(df)
    assert len(prof) == 24 and prof.loc[12, "occupied_share"] > 0.9
    daily = daily_summary(df)
    assert daily["occupied_hours"].iloc[0] == pytest.approx(9.0, abs=0.5)


def test_sql_queries_run():
    df, _ = make_frame()
    con = to_sqlite(df)
    assert set(load_queries()) == {"co2_band_share", "hourly_profile", "worst_days", "indoor_outdoor_gap"}
    results = run_all(con)
    assert results["co2_band_share"]["share_pct"].sum() == pytest.approx(100.0, abs=0.2)
    assert len(results["hourly_profile"]) == 24
