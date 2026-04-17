"""Fit OLS regression coefficients for translating Stanhope weather → park stations.

For each park station, fits per-variable OLS:
    park_var = slope × stanhope_var + intercept

Uses 80/20 train/test split to validate translation quality (RMSE).

Outputs:
    data/processed/ols_coefficients.json  — slopes, intercepts, R², RMSE
    data/processed/ols_validation.json    — holdout RMSE per variable per station
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "processed"

STANHOPE = "stanhope"
PARK_STATIONS = ["cavendish", "greenwich", "north_rustico", "stanley_bridge", "tracadie"]
VARIABLES = ["air_temperature_c", "relative_humidity_pct", "wind_speed_kmh", "rain_mm"]

TRAIN_FRAC = 0.8
RANDOM_SEED = 42


def load_station(station: str) -> pd.DataFrame:
    """Load hourly CSV for a station."""
    path = DATA_DIR / station / "station_hourly.csv"
    df = pd.read_csv(path, parse_dates=["timestamp_utc"], low_memory=False)
    df = df.rename(columns={"timestamp_utc": "ts"})
    return df


def build_paired_dataset() -> dict[str, pd.DataFrame]:
    """Inner-join Stanhope with each park station on timestamp.

    Returns dict mapping station name → DataFrame with columns:
        {var}_sth, {var}_{station} for each variable in VARIABLES.
    """
    stanhope = load_station(STANHOPE)
    stanhope_ts = set(stanhope["ts"])

    results = {}
    for station in PARK_STATIONS:
        park = load_station(station)
        park_ts = set(park["ts"])
        paired_ts = stanhope_ts & park_ts

        sth_sub = stanhope[stanhope["ts"].isin(paired_ts)].set_index("ts")
        park_sub = park[park["ts"].isin(paired_ts)].set_index("ts")

        merged = sth_sub[VARIABLES].join(
            park_sub[VARIABLES], lsuffix="_sth", rsuffix=f"_{station}"
        )
        merged = merged.dropna()
        results[station] = merged

    return results


def fit_ols(x: np.ndarray, y: np.ndarray) -> dict:
    """Fit simple linear regression y = slope*x + intercept.

    Returns dict with slope, intercept, r_squared, std_error, n.
    """
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    return {
        "slope": round(float(slope), 6),
        "intercept": round(float(intercept), 4),
        "r_squared": round(float(r_value**2), 4),
        "p_value": float(p_value),
        "std_error": round(float(std_err), 6),
        "n": int(len(x)),
    }


def validate_holdout(
    paired: pd.DataFrame, station: str, train_idx: pd.Index, test_idx: pd.Index
) -> dict:
    """Compute RMSE on holdout set using OLS fitted on train set.

    Returns nested dict: {variable: {rmse, mae, bias, train_n, test_n}}.
    """
    results = {}
    for var in VARIABLES:
        sth_col = f"{var}_sth"
        park_col = f"{var}_{station}"

        x_train = paired.loc[train_idx, sth_col].values
        y_train = paired.loc[train_idx, park_col].values
        x_test = paired.loc[test_idx, sth_col].values
        y_test = paired.loc[test_idx, park_col].values

        slope, intercept, _, _, _ = stats.linregress(x_train, y_train)
        y_pred = slope * x_test + intercept

        residuals = y_test - y_pred
        rmse = float(np.sqrt(np.mean(residuals**2)))
        mae = float(np.mean(np.abs(residuals)))
        bias = float(np.mean(residuals))

        results[var] = {
            "rmse": round(rmse, 4),
            "mae": round(mae, 4),
            "bias": round(bias, 4),
            "train_n": int(len(x_train)),
            "test_n": int(len(x_test)),
        }
    return results


def main() -> None:
    print("Loading paired hourly data...")
    paired_data = build_paired_dataset()

    for station, df in paired_data.items():
        print(f"  {station}: {len(df)} complete paired records")

    print(f"\nFitting OLS on full dataset ({TRAIN_FRAC:.0%} train, {1-TRAIN_FRAC:.0%} holdout)...")

    coefficients = {}
    validation = {}

    for station, paired in paired_data.items():
        rng = np.random.default_rng(RANDOM_SEED)
        idx = paired.index.to_numpy()
        rng.shuffle(idx)
        split = int(len(idx) * TRAIN_FRAC)
        train_idx = pd.Index(idx[:split])
        test_idx = pd.Index(idx[split:])

        # Fit on train set
        station_coeffs = {}
        for var in VARIABLES:
            sth_col = f"{var}_sth"
            park_col = f"{var}_{station}"
            result = fit_ols(
                paired.loc[train_idx, sth_col].values,
                paired.loc[train_idx, park_col].values,
            )
            station_coeffs[var] = result
            print(
                f"  {station:15s} {var:25s}  "
                f"slope={result['slope']:8.4f}  intercept={result['intercept']:8.3f}  "
                f"R²={result['r_squared']:.4f}  n={result['n']}"
            )

        coefficients[station] = station_coeffs

        # Validate on holdout
        validation[station] = validate_holdout(paired, station, train_idx, test_idx)

    # Print validation summary
    print("\n--- Holdout Validation (RMSE) ---")
    for station, vals in validation.items():
        print(f"\n  {station}:")
        for var, metrics in vals.items():
            print(
                f"    {var:25s}  RMSE={metrics['rmse']:7.3f}  "
                f"MAE={metrics['mae']:7.3f}  bias={metrics['bias']:+7.3f}  "
                f"(n_train={metrics['train_n']}, n_test={metrics['test_n']})"
            )

    # Save outputs
    out_coeffs = DATA_DIR / "ols_coefficients.json"
    out_valid = DATA_DIR / "ols_validation.json"

    out_coeffs.write_text(json.dumps(coefficients, indent=2) + "\n")
    out_valid.write_text(json.dumps(validation, indent=2) + "\n")

    print(f"\nSaved coefficients → {out_coeffs}")
    print(f"Saved validation   → {out_valid}")


if __name__ == "__main__":
    main()
