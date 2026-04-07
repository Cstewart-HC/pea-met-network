#!/usr/bin/env python3
"""Backfill historical FWI for all stations from ECCC hourly observations.

Reads the QA/QC'd hourly CSVs in data/processed/{station}/station_hourly.csv,
recomputes the full FWI chain (FFMC → DMC → DC → ISI → BUI → FWI) from the
start of each station's record, and writes the result back into the same file.

Uses compute_fwi_series as the single source of truth for FWI computation,
ensuring the reference chain in station_hourly.csv is identical to what the
forecast pipeline produces.

All three FWI code paths (ETL cleaning, forecast, and backfill) now share
the same Van Wagner fire-day convention via compute_fwi_series:
  - Fire day D spans 14:00 LST on calendar D-1 to 13:59 LST on D
  - ZoneInfo("America/Halifax") for DST-safe local time
  - Observation closest to 14:00 LST for temp/RH
  - Rain accumulated across the full fire-day window

Startup indices: FFMC=85, DMC=6, DC=15 (standard spring defaults).

Usage:
    python scripts/backfill_historical_fwi.py [--station STATION] [--dry-run]
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pea_met_network.fwi_forecast import (
    ALL_STATIONS,
    compute_fwi_series,
    DEFAULT_FFMC0,
    DEFAULT_DMC0,
    DEFAULT_DC0,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

DATA_DIR = PROJECT_ROOT / "data" / "processed"

REQUIRED_COLS = ["air_temperature_c", "relative_humidity_pct", "wind_speed_kmh", "rain_mm"]
FWI_COLS = ["ffmc", "dmc", "dc", "isi", "bui", "fwi"]


def compute_fwi_for_station(
    df: pd.DataFrame,
    station_name: str,
    lat: float,
) -> pd.DataFrame:
    """Compute full FWI chain via compute_fwi_series (single source of truth).

    Delegates all fire-day assignment, daily aggregation, and FWI math to
    compute_fwi_series so the backfill is always in lockstep with the
    forecast pipeline.
    """
    from zoneinfo import ZoneInfo

    HALIFAX_TZ = ZoneInfo("America/Halifax")

    df = df.copy()
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    df = df.sort_values("timestamp_utc").reset_index(drop=True)

    # Flag rows with complete weather data
    df["can_compute"] = df[REQUIRED_COLS].notna().all(axis=1)

    if not df["can_compute"].any():
        logger.warning("No rows with complete weather data for %s", station_name)
        return df

    # Build Station-like object for duck typing
    class _Stn:
        def __init__(self, lat: float):
            self.lat = lat

    # Run compute_fwi_series on the full record
    computable = df[df["can_compute"]].copy()
    weather = computable[REQUIRED_COLS].copy()
    weather.index = computable["timestamp_utc"]

    result = compute_fwi_series(
        weather, _Stn(lat),
        ffmc0=DEFAULT_FFMC0,
        dmc0=DEFAULT_DMC0,
        dc0=DEFAULT_DC0,
    )

    # Map results back onto the full DataFrame
    # compute_fwi_series preserves the input index, which is a subset
    # of the full DataFrame's index (only computable rows).
    for col in ["FFMC", "DMC", "DC", "ISI", "BUI", "FWI"]:
        df_col = col.lower()
        df.loc[computable.index, df_col] = result[col].values

    rows_updated = int(df["can_compute"].sum())
    logger.info(
        "%s: updated %d/%d rows (%d had incomplete data)",
        station_name, rows_updated, len(df), len(df) - rows_updated,
    )
    return df


def process_station(station_name: str, dry_run: bool = False) -> None:
    """Process a single station."""
    station_map = {s.name: s for s in ALL_STATIONS}
    stn = station_map.get(station_name)
    if not stn:
        logger.error("Unknown station: %s", station_name)
        return

    hourly_path = DATA_DIR / station_name / "station_hourly.csv"
    if not hourly_path.exists():
        logger.error("No hourly data for %s at %s", station_name, hourly_path)
        return

    logger.info("Processing %s from %s", station_name, hourly_path)
    df = pd.read_csv(hourly_path, low_memory=False)

    before_count = df["fwi"].notna().sum()
    logger.info(
        "  Before: %d/%d rows have FWI (%.1f%%)",
        before_count, len(df), 100 * before_count / len(df),
    )

    # Full overwrite — no fill-only mode.  The old ETL values used a
    # different fire-day convention (calendar day, hardcoded DST, max-temp
    # selection).  We need a single source of truth.
    df = compute_fwi_for_station(df, station_name, stn.lat)

    after_count = df["fwi"].notna().sum()
    logger.info(
        "  After:  %d/%d rows have FWI (%.1f%%)",
        after_count, len(df), 100 * after_count / len(df),
    )

    if dry_run:
        logger.info("  (dry run — not writing)")
        return

    # Write back
    df.to_csv(hourly_path, index=False)
    logger.info("  Written to %s", hourly_path)


def main():
    parser = argparse.ArgumentParser(description="Backfill historical FWI for PEINP stations")
    parser.add_argument("--station", "-s", help="Process a single station")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Don't write files")
    args = parser.parse_args()

    stations = [args.station] if args.station else [s.name for s in ALL_STATIONS]

    for name in stations:
        process_station(name, dry_run=args.dry_run)

    logger.info("Done.")


if __name__ == "__main__":
    main()
