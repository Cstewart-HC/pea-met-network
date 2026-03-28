#!/usr/bin/env python3
"""pea_met_network.fwi_diagnostics — FWI chain break diagnostics.

Analyzes FWI calculation output to identify where state chains break,
why they broke, and how many rows were affected.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class ChainBreak:
    """A single chain break event for one moisture code."""

    station: str
    code: str  # "ffmc", "dmc", "dc"
    break_start: str  # ISO timestamp
    break_end: str | None  # ISO timestamp (None = never recovers)
    cause: str  # "input_missing", "quality_enforcement", "startup"
    missing_input: str  # which input column was NaN
    rows_affected: int  # total rows lost due to this break


# Maps each FWI code to its required input columns.
CODE_INPUTS: dict[str, list[str]] = {
    "ffmc": ["air_temperature_c", "relative_humidity_pct", "wind_speed_kmh"],
    "dmc": ["air_temperature_c", "relative_humidity_pct"],
    "dc": ["air_temperature_c"],
}

# Startup defaults for chain recovery.
STARTUP_DEFAULTS: dict[str, float] = {
    "ffmc": 85.0,
    "dmc": 6.0,
    "dc": 15.0,
}


def _find_null_regions(mask: np.ndarray) -> list[tuple[int, int]]:
    """Find contiguous True regions in a boolean mask.

    Returns list of (start_index, end_index) tuples where end_index
    is exclusive (first False after the region, or len(mask)).
    """
    regions = []
    in_region = False
    start = -1
    for i in range(len(mask)):
        if mask[i] and not in_region:
            in_region = True
            start = i
        elif not mask[i] and in_region:
            in_region = False
            regions.append((start, i))
    if in_region:
        regions.append((start, len(mask)))
    return regions


def _determine_cause(
    break_time: pd.Timestamp,
    quality_actions: list[dict] | None,
    missing_inputs: list[str],
) -> str:
    """Determine the cause of a chain break."""
    if quality_actions and missing_inputs:
        for action in quality_actions:
            action_time = action.get("timestamp")
            if action_time is None:
                continue
            try:
                action_ts = pd.Timestamp(action_time, tz="UTC")
                if abs((break_time - action_ts).total_seconds()) < 7200:
                    return "quality_enforcement"
            except (ValueError, TypeError):
                pass
    return "input_missing"


def diagnose_chain_breaks(
    hourly_df: pd.DataFrame,
    station: str,
    quality_actions: list[dict] | None = None,
) -> list[ChainBreak]:
    """Analyze FWI columns to identify where state chains break.

    Compares null patterns of each FWI code against its input
    dependencies.  A *chain break* is detected when the code has
    contiguous NaN regions — each region becomes one ChainBreak event.

    Args:
        hourly_df: Hourly station dataframe with FWI columns.
        station: Station name for the report.
        quality_actions: Optional quality enforcement action records.

    Returns:
        List of ChainBreak objects.
    """
    breaks: list[ChainBreak] = []
    ts_col = "timestamp_utc"
    if ts_col not in hourly_df.columns:
        return breaks

    timestamps = pd.to_datetime(hourly_df[ts_col], utc=True)

    for code, input_cols in CODE_INPUTS.items():
        if code not in hourly_df.columns:
            continue

        code_null = hourly_df[code].isna().to_numpy()
        if not code_null.any():
            continue

        null_regions = _find_null_regions(code_null)

        for start_idx, end_idx in null_regions:
            rows_affected = end_idx - start_idx

            # Find which inputs were NaN at the break start.
            missing_inputs: list[str] = []
            for col in input_cols:
                if col in hourly_df.columns:
                    val = hourly_df[col].iloc[start_idx]
                    if pd.isna(val):
                        missing_inputs.append(col)

            break_time = timestamps.iloc[start_idx]
            cause = _determine_cause(
                break_time, quality_actions, missing_inputs
            )

            # break_end: first valid code value after break, or None.
            if end_idx < len(code_null):
                break_end_ts = timestamps.iloc[end_idx].isoformat()
            else:
                break_end_ts = None

            break_start_ts = break_time.isoformat()
            missing_input_str = (
                ", ".join(missing_inputs) if missing_inputs else "unknown"
            )

            breaks.append(
                ChainBreak(
                    station=station,
                    code=code,
                    break_start=break_start_ts,
                    break_end=break_end_ts,
                    cause=cause,
                    missing_input=missing_input_str,
                    rows_affected=rows_affected,
                )
            )

    return breaks


def chain_breaks_to_dataframe(
    breaks: list[ChainBreak],
) -> pd.DataFrame:
    """Convert a list of ChainBreak objects to a DataFrame."""
    if not breaks:
        return pd.DataFrame(
            columns=[
                "station",
                "code",
                "break_start",
                "break_end",
                "cause",
                "missing_input",
                "rows_affected",
            ]
        )

    return pd.DataFrame(
        [
            {
                "station": b.station,
                "code": b.code,
                "break_start": b.break_start,
                "break_end": b.break_end,
                "cause": b.cause,
                "missing_input": b.missing_input,
                "rows_affected": b.rows_affected,
            }
            for b in breaks
        ]
    )
