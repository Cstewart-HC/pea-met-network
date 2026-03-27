"""pea_met_network.quality — Data quality enforcement for PEA Met Network.

Provides:
  - enforce_quality(): run all quality checks on a DataFrame
  - enforce_fwi_outputs(): validate FWI output ranges
  - truncate_date_range(): exclude records before the data start date
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _ts_iso(df: pd.DataFrame, idx) -> str:
    """Return ISO-format timestamp for a row."""
    return pd.Timestamp(df.at[idx, "timestamp_utc"]).isoformat()


# ---------------------------------------------------------------------------
# enforce_quality — main entry point
# ---------------------------------------------------------------------------


def _get_enforcement_action(
    config: dict[str, Any],
    check_type: str,
) -> str:
    """Read the enforcement action for a check type from config.

    Falls back to ``enforcement.default_action`` if the specific
    check type is not listed in ``enforcement.actions``.
    """
    actions = config.get("enforcement", {}).get("actions", {})
    default = config.get("enforcement", {}).get("default_action", "set_nan")
    return actions.get(check_type, default)


def _check_value_ranges(
    df: pd.DataFrame,
    config: dict[str, Any],
    flag_map: dict[int, list[str]],
) -> list[dict[str, Any]]:
    """Check value ranges and apply configured action."""
    actions_list: list[dict[str, Any]] = []
    value_ranges = config.get("value_ranges", {})
    action = _get_enforcement_action(config, "out_of_range")
    for var, (lo, hi) in value_ranges.items():
        if var not in df.columns:
            continue
        mask = df[var].notna() & ((df[var] < lo) | (df[var] > hi))
        for idx in df.index[mask]:
            actions_list.append(
                {
                    "station": df.at[idx, "station"],
                    "timestamp_utc": _ts_iso(df, idx),
                    "check_type": "value_range",
                    "variable": var,
                    "original_value": df.at[idx, var],
                    "action": action,
                    "rule": f"VR_{var}",
                }
            )
            flag_map[idx].append(f"value_range:{var}")
            if action == "set_nan":
                df.at[idx, var] = np.nan
    return actions_list


def _check_rate_of_change(
    df: pd.DataFrame,
    config: dict[str, Any],
    flag_map: dict[int, list[str]],
) -> list[dict[str, Any]]:
    """Detect rate-of-change violations and apply configured action."""
    actions_list: list[dict[str, Any]] = []
    roc_config = config.get("rate_of_change", {})
    max_delta = roc_config.get("max_delta", {})
    action = _get_enforcement_action(config, "rate_of_change")
    for var, threshold in max_delta.items():
        if var not in df.columns:
            continue
        col = df[var]
        delta = col.diff().abs()
        trigger = (
            delta.notna()
            & (delta > threshold)
            & col.notna()
            & col.shift(1).notna()
        )
        for idx in df.index[trigger]:
            actions_list.append(
                {
                    "station": df.at[idx, "station"],
                    "timestamp_utc": _ts_iso(df, idx),
                    "check_type": "rate_of_change",
                    "variable": var,
                    "original_value": df.at[idx, var],
                    "action": action,
                    "rule": f"RoC_{var}",
                }
            )
            flag_map[idx].append(f"rate_of_change:{var}")
            if action == "set_nan":
                df.at[idx, var] = np.nan
    return actions_list


def _check_cross_variable(
    df: pd.DataFrame,
    config: dict[str, Any],
    flag_map: dict[int, list[str]],
) -> list[dict[str, Any]]:
    """Cross-variable consistency checks (e.g. rain + low RH)."""
    actions_list: list[dict[str, Any]] = []
    cv_config = config.get("cross_variable_checks", {})
    rain_cfg = cv_config.get("rain_rh_correlation", {})
    if not rain_cfg.get("enabled", True):
        return actions_list
    min_rh = rain_cfg.get("min_rh_for_rain", 70.0)
    action = _get_enforcement_action(config, "cross_variable")
    rain_col = "rain_mm"
    rh_col = "relative_humidity_pct"
    if rain_col not in df.columns or rh_col not in df.columns:
        return actions_list
    trigger = (
        df[rain_col].notna()
        & (df[rain_col] > 0)
        & df[rh_col].notna()
        & (df[rh_col] < min_rh)
    )
    for idx in df.index[trigger]:
        actions_list.append(
            {
                "station": df.at[idx, "station"],
                "timestamp_utc": _ts_iso(df, idx),
                "check_type": "cross_variable",
                "variable": rain_col,
                "original_value": df.at[idx, rain_col],
                "action": action,
                "rule": "CV_rain_rh",
            }
        )
        flag_map[idx].append("cross_variable:rain_rh")
        if action == "set_nan":
            df.at[idx, rain_col] = np.nan
    return actions_list


def _check_flatline(
    df: pd.DataFrame,
    config: dict[str, Any],
    flag_map: dict[int, list[str]],
) -> list[dict[str, Any]]:
    """Detect flatline sequences and apply configured action."""
    actions_list: list[dict[str, Any]] = []
    flatline_cfg = config.get("flatline", {})
    if not flatline_cfg.get("enabled", False):
        return actions_list
    threshold = flatline_cfg.get("threshold_hours", 6)
    flatline_vars = flatline_cfg.get("variables", [])
    action = _get_enforcement_action(config, "flatline")
    for var in flatline_vars:
        if var not in df.columns:
            continue
        for station, group in df.groupby("station", sort=False):
            grp = group[var]
            run_length = 0
            for pos, (idx, val) in enumerate(grp.items()):
                if pd.isna(val):
                    run_length = 0
                    continue
                prev = grp.iloc[pos - 1]
                if pos > 0 and not pd.isna(prev) and prev == val:
                    run_length += 1
                else:
                    run_length = 1
                if run_length >= threshold:
                    actions_list.append(
                        {
                            "station": station,
                            "timestamp_utc": _ts_iso(df, idx),
                            "check_type": "flatline",
                            "variable": var,
                            "original_value": val,
                            "action": action,
                            "rule": f"FL_{var}",
                        }
                    )
                    flag_map[idx].append(f"flatline:{var}")
    return actions_list


def _build_flags_column(
    df: pd.DataFrame,
    flag_map: dict[int, list[str]],
) -> pd.Series:
    """Build _quality_flags column from the flag map."""
    import json

    flags = pd.Series([None] * len(df), index=df.index, dtype=object)
    for idx, fl in flag_map.items():
        if fl:
            flags.at[idx] = json.dumps(fl)
    return flags


def enforce_quality(
    df: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Run all quality checks on *df* and return (cleaned_df, actions).

    Parameters
    ----------
    df : DataFrame with at least timestamp_utc, station, and the
        monitored columns.
    config : cleaning-config.json loaded as a dict.

    Returns
    -------
    (df_out, actions) where *df_out* has a ``_quality_flags`` column
    and *actions* is a list of structured action records.
    """
    df_out = df.copy()
    actions: list[dict[str, Any]] = []
    flag_map: dict[int, list[str]] = {i: [] for i in range(len(df_out))}

    actions.extend(_check_value_ranges(df_out, config, flag_map))
    actions.extend(_check_rate_of_change(df_out, config, flag_map))
    actions.extend(_check_cross_variable(df_out, config, flag_map))
    actions.extend(_check_flatline(df_out, config, flag_map))

    df_out["_quality_flags"] = _build_flags_column(df_out, flag_map)
    return df_out, actions


# ---------------------------------------------------------------------------
# enforce_fwi_outputs — FWI output range validation
# ---------------------------------------------------------------------------


def enforce_fwi_outputs(
    df: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Validate FWI output columns against configured ranges.

    Applies the configured action for fwi_out_of_range check type.
    Returns (df_out, actions).
    """
    df_out = df.copy()
    actions: list[dict[str, Any]] = []
    fwi_ranges = config.get("fwi_output_ranges", {})
    action = _get_enforcement_action(config, "fwi_out_of_range")
    for var, (lo, hi) in fwi_ranges.items():
        if var not in df_out.columns:
            continue
        if hi is None:
            # No upper limit — only check lower bound
            mask = df_out[var].notna() & (df_out[var] < lo)
        else:
            mask = df_out[var].notna() & (
                (df_out[var] < lo) | (df_out[var] > hi)
            )
        for idx in df_out.index[mask]:
            actions.append(
                {
                    "station": df_out.at[idx, "station"],
                    "timestamp_utc": _ts_iso(df_out, idx),
                    "check_type": "fwi_output_range",
                    "variable": var,
                    "original_value": df_out.at[idx, var],
                    "action": action,
                    "rule": f"FWI_{var}",
                }
            )
            if action == "set_nan":
                df_out.at[idx, var] = np.nan
    return df_out, actions


# ---------------------------------------------------------------------------
# truncate_date_range — exclude records before data start date
# ---------------------------------------------------------------------------


def truncate_date_range(
    df: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Remove rows with timestamp_utc before the configured start date."""
    if len(df) == 0:
        return df.copy()
    start_str = config.get("date_range", {}).get("start", "2023-04-01")
    cutoff = pd.Timestamp(start_str, tz="UTC")
    ts_col = df["timestamp_utc"]
    if ts_col.dt.tz is None:
        ts_col = ts_col.dt.tz_localize("UTC")
    elif ts_col.dt.tz != cutoff.tz:
        ts_col = ts_col.dt.tz_convert("UTC")
    mask = ts_col >= cutoff
    return df.loc[mask].reset_index(drop=True)
