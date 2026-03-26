"""Stanhope validation utilities — compare PEINP stations
against ECCC reference.

Provides:
    validate_against_reference — pairwise comparison of one station vs Stanhope
    compare_station_data — general-purpose station data comparison helper
"""

from __future__ import annotations

import pandas as pd


def compare_station_data(
    ref_df: pd.DataFrame,
    cmp_df: pd.DataFrame,
    on: str = "timestamp_utc",
    value_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Merge two station DataFrames and return overlapping rows.

    Parameters
    ----------
    ref_df : DataFrame
        Reference station data (e.g. Stanhope).
    cmp_df : DataFrame
        Comparison station data.
    on : str
        Column to join on (default: ``timestamp_utc``).
    value_cols : list[str] or None
        Columns to keep from each side.  If *None*, all columns are kept
        and suffixed with ``_ref`` / ``_cmp``.

    Returns
    -------
    DataFrame with the overlapping rows from both stations.
    """
    if (
        ref_df.empty
        or cmp_df.empty
        or on not in ref_df.columns
        or on not in cmp_df.columns
    ):
        return pd.DataFrame()

    if value_cols is None:
        merged = ref_df.merge(
            cmp_df, on=on, how="inner", suffixes=("_ref", "_cmp")
        )
        return merged

    keep_ref = [on] + [c for c in value_cols if c in ref_df.columns]
    keep_cmp = [on] + [c for c in value_cols if c in cmp_df.columns]
    merged = (
        ref_df[keep_ref]
        .merge(cmp_df[keep_cmp], on=on, how="inner", suffixes=("_ref", "_cmp"))
    )
    return merged


def validate_against_reference(
    station: str,
    reference_df: pd.DataFrame,
    station_df: pd.DataFrame,
) -> dict:
    """Compare a local station's daily data against the Stanhope reference.

    Parameters
    ----------
    station : str
        Station name (e.g. ``"greenwich"``).
    reference_df : DataFrame
        Stanhope daily data with at least ``timestamp_utc`` and FWI columns.
    station_df : DataFrame
        Local station daily data with the same columns.

    Returns
    -------
    dict with keys ``station``, ``overlap_days``, and
    ``mean_abs_diff_<col>`` for each FWI-related column found in both
    DataFrames.
    """
    result: dict = {"station": station, "overlap_days": 0}

    if station_df.empty:
        return result

    fwi_cols = ["ffmc", "dmc", "dc", "isi", "bui", "fwi"]
    existing_cols = [
        c for c in fwi_cols
        if c in reference_df.columns and c in station_df.columns
    ]

    if not existing_cols:
        return result

    merged = compare_station_data(
        reference_df,
        station_df,
        on="timestamp_utc",
        value_cols=existing_cols,
    )

    overlap = len(merged)
    result["overlap_days"] = overlap

    if overlap == 0:
        for col in existing_cols:
            result[f"mean_abs_diff_{col}"] = None
        return result

    for col in existing_cols:
        ref_col = f"{col}_ref"
        cmp_col = f"{col}_cmp"
        if ref_col in merged.columns and cmp_col in merged.columns:
            diff = merged[ref_col].dropna() - merged[cmp_col].dropna()
            result[f"mean_abs_diff_{col}"] = round(diff.abs().mean(), 4)
        else:
            result[f"mean_abs_diff_{col}"] = None

    return result
