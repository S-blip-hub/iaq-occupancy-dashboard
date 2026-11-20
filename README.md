# Indoor Air Quality & Occupancy Dashboard

[![CI](https://github.com/S-blip-hub/iaq-occupancy-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/S-blip-hub/iaq-occupancy-dashboard/actions/workflows/ci.yml)

Analysis pipeline and web dashboard for paired **indoor and outdoor air-quality sensors** (testo 160 IAQ loggers, 15-minute interval) in a naturally ventilated room. The project cleans the logger exports, infers occupancy from CO₂, runs SQL analyses and publishes an interactive dashboard that works offline and on GitHub Pages.

This is a portfolio implementation of the dashboard I built for **Data Analytics in Building Sciences (AR32203)** at IIT Kharagpur, rewritten in 2026 as a tested Python package with SQL analyses and a dependency-free web front end.

**Stack:** Python (pandas, NumPy, Matplotlib) · SQL (SQLite) · HTML, CSS, JavaScript (Canvas API, no libraries)

## What it does

| Stage | Module | Output |
|---|---|---|
| Load and clean | `iaq/loader.py` | Tidy time-indexed frame; `indoor [ppm]` becomes `in_co2_ppm`, duplicates dropped, impossible values removed |
| Indicators | `iaq/metrics.py` | CO₂ bands, comfort-band share, hourly and daily profiles |
| Occupancy proxy | `iaq/metrics.py` | Room marked "likely occupied" when indoor CO₂ is more than 60 ppm above outdoor or rising faster than 40 ppm/h (3-reading median filter) |
| SQL analyses | `sql/analysis.sql`, `iaq/store.py` | CO₂ band shares, hourly profile, worst days, indoor–outdoor gap |
| Dashboard | `dashboard/` | Summary cards, average-day chart with metric toggle, day-by-day chart with tooltips, worst-days table |

## Findings from the monitored room (55 days, 5,248 readings)

| Indicator | Value |
|---|---|
| Mean indoor CO₂ | 433 ppm (95th percentile 687 ppm) |
| Peak indoor CO₂ | 1,496 ppm |
| Readings above 1,200 ppm | 0.4% |
| Inferred occupancy | 22.8% of readings |
| Mean CO₂, occupied vs unoccupied | 602 ppm vs 383 ppm |
| Readings inside 20–30 °C and 30–70% RH | 33% |

- **Ventilation is adequate most of the time.** 97% of readings stay below 800 ppm, but a few occupied evenings reach 1,000–1,500 ppm.
- **Occupancy follows the day.** CO₂ starts rising around 09:00 and peaks near 17:00, about 124 ppm above outdoor air on an average day.
- **The room is a heat trap at night.** It is about 3 °C cooler than outside at midday but 2.5–3.3 °C warmer between midnight and 06:00, because the building mass releases the heat it absorbed during the day. This is why night-time ventilation matters in this climate.

Values come from the build script (`python -m iaq.build`); the SQL result tables are written to `outputs/`.

## Quick start

```bash
pip install -r requirements.txt
bash scripts/run.sh path/to/testo_export.xlsx      # build data, figures and SQL tables, run tests
open dashboard/index.html                        # or serve the folder with GitHub Pages
```

Or step by step:

```bash
python -m iaq.build path/to/testo_export.xlsx --sheet "master sheet"
python -m pytest
```

The export needs a matched timestamp column and `indoor [...]` / `outdoor [...]` columns for ppm, °C, mbar, %RH, °C td and g/m³, as produced by the testo software.

## Data

The raw sensor export belongs to the course and is not redistributed here. `dashboard/data.js` contains only the aggregated hourly and daily values used by the dashboard.

## Method notes

- **CO₂ bands** (< 800, 800–1,200, > 1,200 ppm) are indicative ventilation-feedback bands, not a regulatory limit.
- **Comfort band** is a fixed 20–30 °C and 30–70% RH screen. An adaptive comfort model would accept warmer temperatures in hot months.
- **Occupancy** is inferred from CO₂, so it measures "people producing CO₂ in a ventilated room", not a head count. Open windows can hide occupancy, and the first readings after people arrive can lag.

## Project structure

```
iaq/            loader, metrics, SQLite store, build script
sql/            analysis queries
dashboard/      index.html, style.css, app.js, data.js (generated)
scripts/run.sh  one-command build and test
tests/          pytest suite
```

## Author

Shrey Singh, B.Arch, Department of Architecture and Regional Planning, IIT Kharagpur.

## License

MIT
