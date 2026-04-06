"""Compare OLS-translated forecasts against direct OWM per-station fetches.

Fetches OWM One Call 3.0 for all 6 stations, then:
1. Translates Stanhope → each park via OLS
2. Computes FWI both ways (OLS-translated vs direct)
3. Reports divergence: mean error, max error, bias per variable and FWI component

Usage:
    .venv/bin/python scripts/validate_ols_vs_direct.py
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import numpy as np

# Add src to path
import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pea_met_network.fwi_forecast import (
    STANHOPE,
    PARK_STATIONS,
    VARIABLES,
    fetch_forecast,
    parse_hourly_weather,
    translate_to_station,
    compute_fwi_series,
    load_coefficients,
)

logging.basicConfig(level=logging.WARNING)


def main() -> None:
    key = os.environ.get("openweather_key")
    if not key:
        raise EnvironmentError("openweather_key env var not set")

    coeffs = load_coefficients()

    # --- Fetch all 6 stations ---
    print("Fetching OWM for all 6 stations...")
    all_stations = [STANHOPE] + PARK_STATIONS
    direct = {}
    for stn in all_stations:
        data = fetch_forecast(stn)
        direct[stn.name] = parse_hourly_weather(data)

    sth = direct["stanhope"]

    # --- Part A: Spatial divergence (Stanhope direct vs park direct) ---
    print("\n" + "=" * 70)
    print("PART A: Direct OWM spatial divergence (Stanhope vs park)")
    print("=" * 70)

    spatial = {}
    for park in PARK_STATIONS:
        merged = sth.join(direct[park.name], lsuffix="_sth", rsuffix="_pk")
        station_spatial = {}
        for var in VARIABLES:
            diff = (merged[f"{var}_pk"] - merged[f"{var}_sth"]).abs()
            bias = (merged[f"{var}_pk"] - merged[f"{var}_sth"]).mean()
            station_spatial[var] = {
                "mean_diff": round(float(diff.mean()), 3),
                "max_diff": round(float(diff.max()), 3),
                "bias": round(float(bias), 3),
            }
            print(
                f"  {park.name:15s} {var:25s}  "
                f"mean={station_spatial[var]['mean_diff']:6.2f}  "
                f"max={station_spatial[var]['max_diff']:6.2f}  "
                f"bias={station_spatial[var]['bias']:+6.2f}"
            )
        spatial[park.name] = station_spatial
        print()

    # --- Part B: OLS-translated vs Direct OWM ---
    print("=" * 70)
    print("PART B: OLS-translated vs Direct OWM per station")
    print("=" * 70)

    ols_comparison = {}
    for park in PARK_STATIONS:
        ols_weather = translate_to_station(sth, park.name, coeffs)
        merged = direct[park.name].join(ols_weather, lsuffix="_direct", rsuffix="_ols")

        station_comp = {}
        print(f"\n  {park.name}:")

        # Weather variable errors
        for var in VARIABLES:
            diff = (merged[f"{var}_ols"] - merged[f"{var}_direct"]).abs()
            bias = (merged[f"{var}_ols"] - merged[f"{var}_direct"]).mean()
            station_comp[var] = {
                "mean_err": round(float(diff.mean()), 3),
                "max_err": round(float(diff.max()), 3),
                "bias": round(float(bias), 3),
            }
            print(
                f"    {var:25s}  "
                f"mean={station_comp[var]['mean_err']:6.2f}  "
                f"max={station_comp[var]['max_err']:6.2f}  "
                f"bias={station_comp[var]['bias']:+6.2f}"
            )

        # FWI component errors
        fwi_direct = compute_fwi_series(direct[park.name], park)
        fwi_ols = compute_fwi_series(ols_weather, park)
        fwi_merged = fwi_direct.join(fwi_ols, lsuffix="_direct", rsuffix="_ols")

        fwi_comp = {}
        for col in ["FFMC", "DMC", "DC", "ISI", "BUI", "FWI"]:
            diff = (fwi_merged[f"{col}_ols"] - fwi_merged[f"{col}_direct"]).abs()
            bias = (fwi_merged[f"{col}_ols"] - fwi_merged[f"{col}_direct"]).mean()
            fwi_comp[col] = {
                "mean_err": round(float(diff.mean()), 3),
                "max_err": round(float(diff.max()), 3),
                "bias": round(float(bias), 3),
            }
            print(
                f"    FWI-{col:3s}              "
                f"mean={fwi_comp[col]['mean_err']:6.2f}  "
                f"max={fwi_comp[col]['max_err']:6.2f}  "
                f"bias={fwi_comp[col]['bias']:+6.2f}"
            )

        station_comp["fwi_components"] = fwi_comp
        ols_comparison[park.name] = station_comp

    # --- Summary ---
    print("\n" + "=" * 70)
    print("SUMMARY: Is single-point OLS sufficient?")
    print("=" * 70)

    for park in PARK_STATIONS:
        ols_err = ols_comparison[park.name]["fwi_components"]["FWI"]["mean_err"]
        spatial_diff = spatial[park.name]["air_temperature_c"]["mean_diff"]
        ols_weather_err = ols_comparison[park.name]["air_temperature_c"]["mean_err"]
        verdict = "GOOD" if ols_err < 2.0 else ("OK" if ols_err < 4.0 else "POOR")
        print(
            f"  {park.name:15s}  spatial_temp_diff={spatial_diff:.2f}°C  "
            f"OLS_weather_err={ols_weather_err:.2f}°C  "
            f"FWI_mean_err={ols_err:.2f}  [{verdict}]"
        )

    # Save results
    out = {
        "spatial_divergence": spatial,
        "ols_vs_direct": ols_comparison,
    }
    out_path = PROJECT_ROOT / "data" / "forecasts" / "ols_validation_report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\nSaved → {out_path}")


if __name__ == "__main__":
    main()
