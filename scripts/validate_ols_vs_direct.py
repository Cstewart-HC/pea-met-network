#!/usr/bin/env python3
"""Validate direct OWM FWI computation against pipeline results.

Fetches current OWM data for all 6 stations, computes FWI via
compute_fwi_series(), and saves a comparison snapshot.

Usage:
    python scripts/validate_ols_vs_direct.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from pea_met_network.fwi_forecast import (
    _fetch_owm_station,
    compute_fwi_series,
    STANHOPE,
    PARK_STATIONS,
)


def main() -> None:
    print("=== Direct OWM FWI Validation ===\n")

    stations = [STANHOPE] + PARK_STATIONS
    results = []

    for station in stations:
        name = station["name"]
        print(f"  Fetching OWM for {name}...", end=" ", flush=True)
        try:
            df = _fetch_owm_station(station, hours=48)
        except Exception as e:
            print(f"ERROR: {e}")
            continue

        if df is None or df.empty:
            print("no data")
            continue

        print(f"{len(df)} rows")

        # Compute FWI from direct OWM obs
        fwis = compute_fwi_series(
            temp=df["temp_c"].values,
            rh=df["rh_pct"].values,
            wind=df["wind_mps"].values,
            rain=df["rain_mm"].values,
            timestamps=df.index,
        )

        fwi_series = fwis.get("FWI", pd.Series(dtype=float))
        if fwi_series.empty:
            print(f"    {name}: no valid FWI values")
            continue

        latest_fwi = fwi_series.iloc[-1]
        latest_ts = str(fwi_series.index[-1])
        max_fwi = fwi_series.max()

        results.append({
            "station": name,
            "latest_fwi": round(float(latest_fwi), 2),
            "max_fwi": round(float(max_fwi), 2),
            "rows": len(df),
            "latest_timestamp": latest_ts,
        })
        print(f"    Latest FWI: {latest_fwi:.2f}, Max: {max_fwi:.2f}")

    if not results:
        print("\nNo results obtained.")
        return

    # Summary
    print("\n--- Summary ---")
    print(f"{'Station':20s} | {'Latest FWI':>10s} | {'Max FWI':>10s} | Rows")
    print("-" * 60)
    for r in results:
        print(f"{r['station']:20s} | {r['latest_fwi']:10.2f} | {r['max_fwi']:10.2f} | {r['rows']}")

    # Save report
    output_dir = REPO_ROOT / "data" / "forecasts"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "owm_validation_report.json"

    report = {
        "method": "direct_owm_fwi",
        "stations": results,
        "note": "Direct OWM fetch + compute_fwi_series for each station.",
    }
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to {report_path}")


if __name__ == "__main__":
    main()
