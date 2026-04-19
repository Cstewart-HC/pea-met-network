#!/usr/bin/env python3
"""Validate OWM RH bias correction against Greenwich observed RH.

Greenwich has an RH sensor, so we can pretend it's missing and compare
three estimation methods against the hidden truth:

  1. VP continuity from Cavendish (P1 internal donor)
  2. OWM bias-corrected RH (bias estimated from Cavendish/N. Rustico/Greenwich)
  3. Raw OWM RH (no correction)

Metrics: MAE, RMSE, bias (mean error) for each method.

Usage:
    python scripts/validate_owm_rh_bias.py
"""

from __future__ import annotations

import logging
import statistics
from datetime import datetime, timezone

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def fetch_licor_and_owm():
    """Fetch Licor obs and OWM forecast for all park stations."""
    from pea_met_network.licor_adapter import LicorAdapter

    adapter = LicorAdapter()
    obs_data = adapter.fetch_recent(hours=6)
    return obs_data


def fetch_owm_for_stations():
    """Fetch raw OWM for all park stations."""
    from pea_met_network.fwi_forecast import fetch_all_stations, PARK_STATIONS
    return fetch_all_stations(PARK_STATIONS)


def vp_continuity_rh(
    target_df: pd.DataFrame,
    target_name: str,
    donor_name: str,
    obs_data: dict[str, pd.DataFrame],
) -> pd.Series:
    """Compute VP continuity RH from a donor station."""
    from pea_met_network.cross_station_impute import (
        DonorAssignment,
        impute_cross_station,
    )

    donors = [
        DonorAssignment(target_name, "relative_humidity_pct", 1, donor_name, "internal"),
    ]

    # Work on a copy with RH nulled out
    target_copy = target_df.copy()
    target_copy["relative_humidity_pct"] = float("nan")

    imputed, records = impute_cross_station(
        target_copy,
        station=target_name,
        donor_assignments=donors,
        internal_hourly=obs_data,
    )

    return imputed["relative_humidity_pct"]


def owm_bias_corrected_rh(
    target_name: str,
    owm_raw: dict[str, pd.DataFrame],
    obs_data: dict[str, pd.DataFrame],
    donors: list[str],
) -> pd.Series:
    """Compute OWM bias-corrected RH for a target station."""
    if target_name not in owm_raw:
        return pd.Series(dtype=float)

    owm_target = owm_raw[target_name]
    if "relative_humidity_pct" not in owm_target.columns:
        return pd.Series(dtype=float)

    # Collect biases from donors
    biases: list[float] = []
    for donor in donors:
        if donor not in obs_data or donor not in owm_raw:
            continue
        obs_d = obs_data[donor]
        owm_d = owm_raw[donor]
        if "relative_humidity_pct" not in obs_d.columns:
            continue
        if "relative_humidity_pct" not in owm_d.columns:
            continue

        overlap = obs_d.index.intersection(owm_d.index)
        overlap = overlap[obs_d.loc[overlap, "relative_humidity_pct"].notna()]
        overlap = overlap[owm_d.loc[overlap, "relative_humidity_pct"].notna()]

        for ts in overlap:
            obs_val = float(obs_d.at[ts, "relative_humidity_pct"])
            owm_val = float(owm_d.at[ts, "relative_humidity_pct"])
            biases.append(owm_val - obs_val)

    if len(biases) < 2:
        logger.warning("Too few bias samples (%d), returning raw OWM", len(biases))
        return owm_target["relative_humidity_pct"].copy()

    median_bias = statistics.median(biases)
    logger.info("Median OWM RH bias from donors: %.1f%% (%d samples)", median_bias, len(biases))

    corrected = owm_target["relative_humidity_pct"] - median_bias
    return corrected.clip(0, 100)


def score_vs_truth(predicted: pd.Series, truth: pd.Series, label: str) -> dict:
    """Compute MAE, RMSE, and mean bias between predicted and truth."""
    valid = truth.notna() & predicted.notna()
    if valid.sum() == 0:
        logger.warning("  %s: no overlapping valid hours", label)
        return {"label": label, "n": 0}

    t = truth.loc[valid].values.astype(float)
    p = predicted.loc[valid].values.astype(float)
    errors = p - t

    mae = float(abs(errors).mean())
    rmse = float((errors ** 2).mean() ** 0.5)
    bias = float(errors.mean())

    result = {"label": label, "n": int(valid.sum()), "mae": mae, "rmse": rmse, "bias": bias}
    logger.info(
        "  %s: n=%d  MAE=%.2f  RMSE=%.2f  bias=%+.2f",
        label, result["n"], mae, rmse, bias,
    )
    return result


def main():
    print("=" * 60)
    print("OWM RH Bias Correction Validation")
    print(f"  Target: Greenwich (pretend RH sensor missing)")
    print(f"  Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    # 1. Fetch data
    print("\n--- Fetching data ---")
    obs_data = fetch_licor_and_owm()
    owm_raw = fetch_owm_for_stations()

    if "greenwich" not in obs_data:
        print("ERROR: No Licor data for Greenwich")
        return

    greenwich_obs = obs_data["greenwich"]
    greenwich_truth = greenwich_obs["relative_humidity_pct"].copy()

    if greenwich_truth.notna().sum() == 0:
        print("ERROR: Greenwich has no observed RH to validate against")
        return

    print(f"  Greenwich: {len(greenwich_obs)} hours, {greenwich_truth.notna().sum()} with RH")

    # 2. VP continuity from Cavendish
    print("\n--- Method 1: VP Continuity (Cavendish → Greenwich) ---")
    vp_rh = vp_continuity_rh(greenwich_obs, "greenwich", "cavendish", obs_data)

    # 3. OWM bias-corrected
    print("\n--- Method 2: OWM Bias-Corrected RH ---")
    donors = ["cavendish", "north_rustico"]
    bc_rh = owm_bias_corrected_rh("greenwich", owm_raw, obs_data, donors)

    # 4. Raw OWM
    print("\n--- Method 3: Raw OWM RH ---")
    raw_owm_rh = owm_raw.get("greenwich", pd.DataFrame()).get(
        "relative_humidity_pct", pd.Series(dtype=float)
    )

    # 5. Score all methods
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    results = []
    results.append(score_vs_truth(vp_rh, greenwich_truth, "VP continuity (Cavendish)"))
    results.append(score_vs_truth(bc_rh, greenwich_truth, "OWM bias-corrected"))
    results.append(score_vs_truth(raw_owm_rh, greenwich_truth, "Raw OWM"))

    # 6. Summary table
    print("\n{:<30s} {:>4s} {:>7s} {:>7s} {:>8s}".format(
        "Method", "N", "MAE", "RMSE", "Bias"
    ))
    print("-" * 60)
    for r in results:
        if r["n"] == 0:
            print(f"{r['label']:<30s} {'--':>4s}")
        else:
            print(f"{r['label']:<30s} {r['n']:>4d} {r['mae']:>6.2f}% {r['rmse']:>6.2f}% {r['bias']:>+7.2f}%")

    # 7. Winner
    scored = [r for r in results if r["n"] > 0]
    if scored:
        best = min(scored, key=lambda r: r["mae"])
        print(f"\n  Best by MAE: {best['label']} ({best['mae']:.2f}%)")

    print()


if __name__ == "__main__":
    main()
