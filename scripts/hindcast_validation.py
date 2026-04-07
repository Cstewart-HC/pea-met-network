#!/usr/bin/env python3
"""Hindcast validation — slide a 48h window across historical obs.

For each window:
  1. Extract startup indices (FFMC, DMC, DC) from the reference chain
     at the hour immediately before the window.
  2. Feed the actual observed weather (temp, RH, wind, rain) into
     ``compute_fwi_series`` as if it were a "perfect forecast."
  3. Compare the computed FWI chain against the reference chain that
     was computed from the full historical record.

This validates:
  - FWI computation correctness (hourly FFMC + daily DMC/DC aggregation)
  - Startup state handling
  - The daily-aggregation logic (warmest-hour temp/RH, accumulated rain)
  - Hourly FFMC chaining across day boundaries

Usage:
    python scripts/hindcast_validation.py                    # defaults
    python scripts/hindcast_validation.py --station greenwich --lead-hours 24
    python scripts/hindcast_validation.py --interval-days 1 --start 2024-05-01 --end 2024-09-30
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pea_met_network.fwi_forecast import (
    ALL_STATIONS,
    STANHOPE,
    compute_fwi_series,
    DEFAULT_FFMC0,
    DEFAULT_DMC0,
    DEFAULT_DC0,
)

# FWI rating class boundaries (Canadian Fire Weather Index System)
FWI_CLASSES = [
    (0, 2, "low"),
    (2, 5, "moderate"),
    (5, 10, "high"),
    (10, 20, "very_high"),
    (20, float("inf"), "extreme"),
]


def fwi_class(fwi: float) -> str:
    for lo, hi, name in FWI_CLASSES:
        if lo <= fwi < hi:
            return name
    return "extreme"


def load_station_data(station: str) -> pd.DataFrame:
    """Load processed hourly data for a station."""
    path = PROJECT_ROOT / "data" / "processed" / station / "station_hourly.csv"
    if not path.exists():
        raise FileNotFoundError(f"No processed data for {station}: {path}")
    df = pd.read_csv(path, parse_dates=["timestamp_utc"])
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    return df.set_index("timestamp_utc").sort_index()


def generate_windows(
    df: pd.DataFrame,
    window_hours: int = 48,
    interval_days: int = 7,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[tuple[datetime, datetime]]:
    """Generate (window_start, window_end) tuples at regular intervals.

    Windows are aligned to fire-day boundaries (14:00 LST = 17:00 UTC in
    ADT, 18:00 UTC in AST) so that every fire day within a window is
    complete.  This ensures compute_fwi_series aggregates the same data
    as the reference chain — no partial fire-day aggregation.
    """
    from zoneinfo import ZoneInfo
    HALIFAX_TZ = ZoneInfo("America/Halifax")

    def _next_fire_day_boundary(ts: pd.Timestamp) -> pd.Timestamp:
        """Advance ts to the next 14:00 LST."""
        local = ts.tz_convert(HALIFAX_TZ)
        # Target: today at 14:00 local, or tomorrow at 14:00 if past it
        target = local.replace(hour=14, minute=0, second=0, microsecond=0)
        if local.hour >= 14:
            target += timedelta(days=1)
        return target.tz_convert("UTC")

    first = df.index.min()
    last = df.index.max()

    # Align first window to the fire-day boundary
    win_start = _next_fire_day_boundary(first + timedelta(hours=window_hours))
    if start:
        s = pd.Timestamp(start, tz=timezone.utc)
        if s > win_start:
            win_start = _next_fire_day_boundary(s)
    if end:
        last = min(last, pd.Timestamp(end, tz=timezone.utc))

    windows = []
    step = timedelta(days=interval_days)
    while win_start + timedelta(hours=window_hours) <= last:
        windows.append((win_start, win_start + timedelta(hours=window_hours)))
        win_start += step
        win_start = _next_fire_day_boundary(win_start)

    return windows


def run_hindcast_window(
    df: pd.DataFrame,
    window_start: datetime,
    window_end: datetime,
    station_name: str,
    station_lat: float,
    use_reference_chain: bool = True,
) -> pd.DataFrame | None:
    """Run a single hindcast window and return comparison results.

    Args:
        df: Full station processed data with reference FWI columns.
        window_start: Start of the forecast window.
        window_end: End of the forecast window.
        station_name: Station name for logging.
        station_lat: Station latitude for FWI computation.
        use_reference_chain: If True, use the reference FFMC/DMC/DC from
            the processed CSV as startup state. If False, compute a
            self-consistency check by running compute_fwi_series over the
            window using the reference's startup indices and comparing
            the hindcast output against a SECOND run over the same data.

    Returns:
        DataFrame with hindcast vs reference/error columns, or None if
        the window has insufficient data.

    Note on fire-day alignment:
        Windows are aligned to 14:00 LST so every fire day within the
        window is complete.  This means compute_fwi_series aggregates
        the same hourly data as the reference chain, producing identical
        DMC/DC.  All startup indices (FFMC, DMC, DC) come from the
        hour before the window, which is the last hour of the previous
        fire day.  All components should be bit-exact.
    """
    from zoneinfo import ZoneInfo
    HALIFAX_TZ = ZoneInfo("America/Halifax")

    def _fire_day(ts: pd.Timestamp) -> "datetime.date":
        local = ts.tz_convert(HALIFAX_TZ)
        return (local + pd.Timedelta(hours=10)).date()

    # Get startup indices:
    #   All three (FFMC, DMC, DC) come from the hour immediately before
    #   the window.  Since windows are aligned to 14:00 LST fire-day
    #   boundaries, the startup hour is the last hour of the previous
    #   fire day — giving us the correct dmc0/dc0 input for
    #   compute_fwi_series to apply the Van Wagner update on the first
    #   complete fire day in the window.
    ffmc_startup = window_start - timedelta(hours=1)
    if ffmc_startup not in df.index:
        before_all = df.index[df.index <= ffmc_startup]
        if len(before_all) == 0:
            return None
        ffmc_startup = before_all[-1]

    ffmc0 = df.loc[ffmc_startup, "ffmc"]
    dmc0 = df.loc[ffmc_startup, "dmc"]
    dc0 = df.loc[ffmc_startup, "dc"]

    # Check startup indices are valid
    if pd.isna(ffmc0) or pd.isna(dmc0) or pd.isna(dc0):
        return None

    # Extract weather data for the window
    mask = (df.index >= window_start) & (df.index < window_end)
    window_df = df.loc[mask]

    # Need all four weather columns
    required = ["air_temperature_c", "relative_humidity_pct", "wind_speed_kmh", "rain_mm"]
    if window_df[required].isna().any().any():
        return None

    if len(window_df) < 12:  # need at least half a day
        return None

    # Build weather DataFrame for compute_fwi_series
    weather = window_df[required].copy()

    # Create a Station-like object (duck typing)
    class _Stn:
        def __init__(self, lat):
            self.lat = lat

    # Compute hindcast FWI
    hindcast = compute_fwi_series(
        weather, _Stn(station_lat),
        ffmc0=float(ffmc0), dmc0=float(dmc0), dc0=float(dc0),
    )

    # Self-consistency check: run the SAME data with the SAME startup twice.
    # Both runs should produce bit-exact results.
    if not use_reference_chain:
        hindcast2 = compute_fwi_series(
            weather, _Stn(station_lat),
            ffmc0=float(ffmc0), dmc0=float(dmc0), dc0=float(dc0),
        )
        reference = hindcast2[["FFMC", "DMC", "DC", "ISI", "BUI", "FWI"]].copy()
        reference.columns = [c.lower() for c in reference.columns]
    else:
        # Align with reference from processed CSV
        reference = window_df[["ffmc", "dmc", "dc", "isi", "bui", "fwi"]].copy()
        # Drop any rows where reference is NaN
        reference = reference.dropna(subset=["ffmc"])

    common_idx = hindcast.index.intersection(reference.index)
    if len(common_idx) < 12:
        return None

    result = pd.DataFrame(index=common_idx)
    for col, ref_col in [
        ("FFMC", "ffmc"),
        ("DMC", "dmc"),
        ("DC", "dc"),
        ("ISI", "isi"),
        ("BUI", "bui"),
        ("FWI", "fwi"),
    ]:
        result[f"hindcast_{col}"] = hindcast.loc[common_idx, col]
        result[f"reference_{col}"] = reference.loc[common_idx, ref_col]
        result[f"error_{col}"] = result[f"hindcast_{col}"] - result[f"reference_{col}"]

    result["lead_hours"] = (result.index - window_start).total_seconds() / 3600
    result["window_start"] = window_start

    return result


def score_results(all_results: list[pd.DataFrame], lead_hours: int) -> dict:
    """Compute aggregate metrics across all windows, optionally filtered by lead hours."""
    if not all_results:
        return {"n_windows": 0}

    combined = pd.concat(all_results)
    if lead_hours is not None:
        combined = combined[combined["lead_hours"] <= lead_hours]

    n_windows = combined["window_start"].nunique()
    n_hours = len(combined)

    metrics = {"n_windows": n_windows, "n_hours": n_hours}

    for col in ["FFMC", "DMC", "DC", "ISI", "BUI", "FWI"]:
        err = combined[f"error_{col}"]
        metrics[f"{col}_mae"] = round(float(err.abs().mean()), 4)
        metrics[f"{col}_rmse"] = round(float(np.sqrt((err ** 2).mean())), 4)
        metrics[f"{col}_bias"] = round(float(err.mean()), 4)
        metrics[f"{col}_max_error"] = round(float(err.abs().max()), 4)

    # FWI rating class accuracy
    if "FWI" in combined.columns:
        ref_classes = combined["reference_FWI"].apply(fwi_class)
        hind_classes = combined["hindcast_FWI"].apply(fwi_class)
        exact = (ref_classes == hind_classes).sum()
        within_1 = 0
        for r, h in zip(ref_classes, hind_classes):
            ri = next(i for i, (lo, hi, _) in enumerate(FWI_CLASSES) if lo <= r < hi)
            hi_idx = next(i for i, (lo, hi, _) in enumerate(FWI_CLASSES) if lo <= h < hi)
            if abs(ri - hi_idx) <= 1:
                within_1 += 1
        metrics["fwi_class_exact_pct"] = round(100 * exact / len(combined), 1)
        metrics["fwi_class_within_1_pct"] = round(100 * within_1 / len(combined), 1)

    # Per-lead-hour bucket MAE for FWI
    if lead_hours is None:
        bucket_maes = {}
        for bucket_start in range(0, 49, 6):
            bucket_end = bucket_start + 6
            mask = (combined["lead_hours"] >= bucket_start) & (combined["lead_hours"] < bucket_end)
            bucket = combined[mask]
            if len(bucket) > 0:
                bucket_maes[f"fwi_mae_{bucket_start}-{bucket_end}h"] = round(float(bucket["error_FWI"].abs().mean()), 4)
        metrics["lead_buckets"] = bucket_maes

    return metrics


def main():
    parser = argparse.ArgumentParser(description="Hindcast validation for FWI pipeline")
    parser.add_argument("--station", default="greenwich", help="Station to validate")
    parser.add_argument("--window-hours", type=int, default=48, help="Forecast window size in hours")
    parser.add_argument("--interval-days", type=int, default=7, help="Days between windows")
    parser.add_argument("--start", default=None, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default=None, help="End date (YYYY-MM-DD)")
    parser.add_argument("--lead-hours", type=int, default=None, help="Only score up to N lead hours")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of text")
    args = parser.parse_args()

    # Resolve station
    station_map = {s.name: s for s in ALL_STATIONS}
    if args.station not in station_map:
        print(f"Unknown station: {args.station}. Choices: {', '.join(station_map.keys())}")
        sys.exit(1)
    stn = station_map[args.station]

    print(f"Loading {args.station} data...")
    df = load_station_data(args.station)
    print(f"  {len(df)} rows, {df.index.min()} → {df.index.max()}")

    # Check for reference FWI columns
    if "ffmc" not in df.columns:
        print(f"ERROR: No reference FFMC column in {args.station} processed data.")
        print("  Run fwi_backfill.py first to generate reference FWI chain.")
        sys.exit(1)

    print(f"\nGenerating {args.window_hours}h windows every {args.interval_days}d...")
    windows = generate_windows(
        df,
        window_hours=args.window_hours,
        interval_days=args.interval_days,
        start=datetime.strptime(args.start, "%Y-%m-%d") if args.start else None,
        end=datetime.strptime(args.end, "%Y-%m-%d") if args.end else None,
    )
    print(f"  {len(windows)} windows generated")

    print(f"\nRunning hindcasts...")
    all_results = []
    skipped = 0
    for i, (ws, we) in enumerate(windows):
        result = run_hindcast_window(df, ws, we, args.station, stn.lat, use_reference_chain=True)
        if result is not None:
            all_results.append(result)
        else:
            skipped += 1

        if (i + 1) % 20 == 0:
            print(f"  {i + 1}/{len(windows)} windows processed "
                  f"({len(all_results)} valid, {skipped} skipped)")

    print(f"  Done: {len(all_results)} valid, {skipped} skipped")

    if not all_results:
        print("No valid windows found. Check data coverage.")
        sys.exit(1)

    # --- Self-consistency check (deterministic reproduction) ---
    print(f"\nRunning self-consistency check (deterministic reproduction)...")
    self_check = []
    for i, (ws, we) in enumerate(windows):
        result = run_hindcast_window(df, ws, we, args.station, stn.lat, use_reference_chain=False)
        if result is not None:
            self_check.append(result)
    self_metrics = score_results(self_check, args.lead_hours)

    # --- Score against reference ---
    metrics = score_results(all_results, args.lead_hours)

    if args.json:
        output = {
            "against_reference": metrics,
            "self_consistency": self_metrics,
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"\n{'=' * 60}")
        print(f"HINDCAST VALIDATION RESULTS — {args.station}")
        print(f"{'=' * 60}")
        print(f"  Windows: {metrics['n_windows']}")
        print(f"  Total hours scored: {metrics['n_hours']}")
        if args.lead_hours:
            print(f"  Lead time filter: ≤{args.lead_hours}h")

        print(f"\n  1. Self-consistency (deterministic reproduction):")
        print(f"     All FWI components should be bit-exact (MAE = 0).")
        if self_metrics["n_windows"] > 0:
            for col in ["FFMC", "DMC", "DC", "ISI", "BUI", "FWI"]:
                mae = self_metrics[f"{col}_mae"]
                status = "✓" if mae == 0.0 else f"✗ ({mae:.6f})"
                print(f"     {col:<6} MAE = {mae:.6f}  {status}")
        else:
            print("     No valid windows for self-check.")

        print(f"\n  2. Against reference chain:")
        print(f"     Windows aligned to 14:00 LST fire-day boundaries.")
        print(f"     All components should be bit-exact (MAE = 0).")
        print(f"     {'Metric':<12} {'MAE':>8} {'RMSE':>8} {'Bias':>8} {'Max Err':>8}")
        print(f"     {'-' * 48}")
        for col in ["FFMC", "DMC", "DC", "ISI", "BUI", "FWI"]:
            mae = metrics[f"{col}_mae"]
            rmse = metrics[f"{col}_rmse"]
            bias = metrics[f"{col}_bias"]
            mx = metrics[f"{col}_max_error"]
            print(f"     {col:<12} {mae:>8.4f} {rmse:>8.4f} {bias:>+8.4f} {mx:>8.4f}")

        if "fwi_class_exact_pct" in metrics:
            print(f"\n     FWI Rating Class Accuracy:")
            print(f"       Exact match:  {metrics['fwi_class_exact_pct']}%")
            print(f"       Within ±1:    {metrics['fwi_class_within_1_pct']}%")

        if "lead_buckets" in metrics:
            print(f"\n     FWI MAE by lead time bucket:")
            for bucket, mae in metrics["lead_buckets"].items():
                print(f"       {bucket:>12}: {mae:.4f}")

        # Worst windows
        combined = pd.concat(all_results)
        window_fwi_mae = combined.groupby("window_start")["error_FWI"].apply(
            lambda x: x.abs().mean()
        ).sort_values(ascending=False)
        print(f"\n     Top 5 worst windows (FWI MAE):")
        for ws_val, mae in window_fwi_mae.head(5).items():
            n_h = len(combined[combined["window_start"] == ws_val])
            print(f"       {str(ws_val)[:19]}  MAE={mae:.4f}  ({n_h}h)")

        print()


if __name__ == "__main__":
    main()
