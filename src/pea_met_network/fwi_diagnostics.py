#!/usr/bin/env python3
"""pea_met_network.fwi_diagnostics — FWI chain break diagnostics.

Analyzes FWI calculation output to identify where state chains break,
why they broke, and how many rows were affected.
"""

from __future__ import annotations

from dataclasses import dataclass, field

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
    cascade_origin: str | None = field(default=None)  # ISO timestamp of original gap (cascade only)


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


def _is_startup(
    start_idx: int,
    end_idx: int,
    code: str,
    hourly_df: pd.DataFrame,
    input_cols: list[str],
) -> bool:
    """Detect startup breaks: DMC/DC NaN at row 0 with all inputs present.

    Startup breaks occur when DMC/DC are NaN for the first few hours of
    data because the daily 14:00 LST calculation hasn't fired yet.
    All required inputs are present — the chain simply hasn't started.

    Returns True if this is a startup break.
    """
    # Must be at the very beginning of the dataset.
    if start_idx != 0:
        return False

    # DMC/DC startup windows are short — typically 0–4 hours before 14:00.
    # FFMC should not have startup breaks (computed hourly from first row).
    if code == "ffmc":
        return False

    # All inputs must be present at the break start.
    for col in input_cols:
        if col in hourly_df.columns:
            val = hourly_df[col].iloc[start_idx]
            if pd.isna(val):
                return False

    # Startup window should be short — less than 24 rows (one day).
    if (end_idx - start_idx) > 24:
        return False

    return True


def _find_cascade_cause(
    start_idx: int,
    code: str,
    hourly_df: pd.DataFrame,
    timestamps: pd.Series,
    input_cols: list[str],
    max_lookback_rows: int = 48,
) -> tuple[str | None, str | None]:
    """Scan backwards (and at start_idx) from a chain break to find the original missing input.

    When FFMC breaks due to missing RH, the NaN cascades into DMC and DC
    (which depend on prior FFMC). By the time DMC/DC NaN appears, the
    original missing input may already be imputed. This function looks
    backwards to find the root cause.

    Also checks FFMC-level inputs (RH, wind) at start_idx itself, since
    DC's direct inputs (temp only) may be present while FFMC inputs are
    NaN at the same row.

    Returns:
        (missing_input_name, cascade_origin_iso) or (None, None).
    """
    # For FFMC, don't cascade — FFMC only depends on immediate inputs.
    if code == "ffmc":
        return None, None

    # Expand input_cols to include upstream dependencies.
    # DMC/DC NaN can cascade from FFMC breaks, which are caused by
    # any of the FFMC inputs (temp, RH, wind).
    cascade_input_cols = list(input_cols)
    ffmc_extra = [
        c for c in CODE_INPUTS["ffmc"]
        if c not in cascade_input_cols
    ]
    all_cascade_cols = cascade_input_cols + ffmc_extra

    best_input: str | None = None
    best_origin_idx: int | None = None

    # Check at start_idx itself (handles the case where break starts at
    # row 0 — lookback window is empty but upstream inputs are NaN).
    for col in all_cascade_cols:
        if col not in hourly_df.columns:
            continue
        if pd.isna(hourly_df[col].iloc[start_idx]):
            if best_origin_idx is None or start_idx > best_origin_idx:
                best_input = col
                best_origin_idx = start_idx

    # Scan backwards for prior NaN gaps.
    lookback_start = max(0, start_idx - max_lookback_rows)

    for col in all_cascade_cols:
        if col not in hourly_df.columns:
            continue
        col_null = hourly_df[col].iloc[lookback_start:start_idx].isna()
        if not col_null.any():
            continue

        # Find the last NaN row in this column within the lookback window.
        null_positions = col_null[col_null].index
        last_null_idx = null_positions[-1]
        if best_origin_idx is None or last_null_idx > best_origin_idx:
            best_input = col
            best_origin_idx = last_null_idx

    if best_input is not None and best_origin_idx is not None:
        origin_ts = timestamps.iloc[best_origin_idx]
        return best_input, origin_ts.isoformat()

    return None, None


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

            # Check for startup breaks (DMC/DC at row 0, all inputs present).
            if _is_startup(start_idx, end_idx, code, hourly_df, input_cols):
                break_time = timestamps.iloc[start_idx]
                break_end_ts = (
                    timestamps.iloc[end_idx].isoformat()
                    if end_idx < len(code_null)
                    else None
                )
                breaks.append(
                    ChainBreak(
                        station=station,
                        code=code,
                        break_start=break_time.isoformat(),
                        break_end=break_end_ts,
                        cause="startup",
                        missing_input="n/a",
                        rows_affected=rows_affected,
                        cascade_origin=None,
                    )
                )
                continue

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

            # If no missing inputs found at break start, look for cascade.
            cascade_origin: str | None = None
            if not missing_inputs:
                cascade_input, cascade_origin = _find_cascade_cause(
                    start_idx, code, hourly_df, timestamps, input_cols
                )
                if cascade_input is not None:
                    missing_inputs = [cascade_input]

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
                    cascade_origin=cascade_origin,
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
                "cascade_origin",
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
                "cascade_origin": b.cascade_origin,
            }
            for b in breaks
        ]
    )
