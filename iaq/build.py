"""Build the dashboard data file, figures and SQL result tables from an export."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .loader import load_export
from .metrics import daily_summary, hourly_profile, summary
from .store import run_all, to_sqlite

ROOT = Path(__file__).resolve().parent.parent


def write_dashboard_data(df, out_js: Path) -> dict:
    payload = {
        "summary": {k: round(v, 3) if isinstance(v, float) else v for k, v in summary(df).items()},
        "hourly": hourly_profile(df).round(2).reset_index().to_dict(orient="records"),
        "daily": [
            {"date": d.strftime("%Y-%m-%d"), **row}
            for d, row in daily_summary(df).to_dict(orient="index").items()
        ],
    }
    out_js.parent.mkdir(parents=True, exist_ok=True)
    out_js.write_text("window.IAQ_DATA = " + json.dumps(payload, separators=(",", ":")) + ";\n")
    return payload


def write_figures(df, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    prof = hourly_profile(df)

    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.plot(prof.index, prof["in_co2_ppm"], color="#1f4e79", lw=2, label="Indoor CO₂")
    ax.plot(prof.index, prof["out_co2_ppm"], color="#9aa5b1", lw=1.5, label="Outdoor CO₂")
    ax2 = ax.twinx()
    ax2.bar(prof.index, prof["occupied_share"] * 100, color="#f0b429", alpha=0.35, label="Likely occupied (%)")
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("CO₂ (ppm)")
    ax2.set_ylabel("Likely occupied (%)")
    ax.set_xticks(range(0, 24, 2))
    ax.legend(loc="upper left", frameon=False)
    ax.set_title("Average daily profile: CO₂ and inferred occupancy")
    fig.tight_layout()
    fig.savefig(out_dir / "hourly_co2_occupancy.png", dpi=140)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.plot(prof.index, prof["in_temp_c"], color="#c0392b", lw=2, label="Indoor")
    ax.plot(prof.index, prof["out_temp_c"], color="#9aa5b1", lw=1.5, label="Outdoor")
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Air temperature (°C)")
    ax.set_xticks(range(0, 24, 2))
    ax.legend(frameon=False)
    ax.set_title("Average daily temperature profile")
    fig.tight_layout()
    fig.savefig(out_dir / "hourly_temperature.png", dpi=140)
    plt.close(fig)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="Build IAQ dashboard data and figures")
    p.add_argument("export", help="testo export (.xlsx or .csv)")
    p.add_argument("--sheet", default="master sheet")
    p.add_argument("--out", default=str(ROOT / "outputs"))
    args = p.parse_args(argv)

    df = load_export(args.export, sheet=args.sheet)
    payload = write_dashboard_data(df, ROOT / "dashboard" / "data.js")
    write_figures(df, Path(args.out))

    con = to_sqlite(df)
    for name, table in run_all(con).items():
        table.to_csv(Path(args.out) / f"sql_{name}.csv", index=False)

    s = payload["summary"]
    print(f"{s['readings']} readings over {s['days']} days")
    for k, v in s.items():
        print(f"  {k:36} {v}")


if __name__ == "__main__":
    main()
