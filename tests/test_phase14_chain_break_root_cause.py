#!/usr/bin/env python3
"""Phase 14 tests — Chain break root cause attribution.

Tests for startup detection, cascade attribution, and the cascade_origin
field in fwi_diagnostics.py.
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from pea_met_network.fwi_diagnostics import (
    ChainBreak,
    _find_cascade_cause,
    _is_startup,
    chain_breaks_to_dataframe,
    diagnose_chain_breaks,
)


def _make_hourly(
    rows: int = 100,
    start: str = "2023-06-01T00:00:00Z",
    ffmc_nan: list[int] | None = None,
    dmc_nan: list[int] | None = None,
    dc_nan: list[int] | None = None,
    rh_nan: list[int] | None = None,
    temp_nan: list[int] | None = None,
    wind_nan: list[int] | None = None,
) -> pd.DataFrame:
    """Build a minimal hourly dataframe for diagnostics testing."""
    ts = pd.date_range(start, periods=rows, freq="h", tz="UTC")
    n = rows
    df = pd.DataFrame(
        {
            "timestamp_utc": ts,
            "air_temperature_c": 20.0 + np.random.default_rng(42).normal(0, 2, n),
            "relative_humidity_pct": 60.0 + np.random.default_rng(43).normal(0, 5, n),
            "wind_speed_kmh": 10.0 + np.random.default_rng(44).normal(0, 1, n),
            "precipitation_mm": 0.0,
            "ffmc": 85.0 + np.random.default_rng(45).normal(0, 3, n),
            "dmc": 10.0 + np.random.default_rng(46).normal(0, 1, n),
            "dc": 200.0 + np.random.default_rng(47).normal(0, 5, n),
        }
    )
    for idx_list, col in [
        (ffmc_nan, "ffmc"),
        (dmc_nan, "dmc"),
        (dc_nan, "dc"),
        (rh_nan, "relative_humidity_pct"),
        (temp_nan, "air_temperature_c"),
        (wind_nan, "wind_speed_kmh"),
    ]:
        if idx_list is not None:
            df.loc[df.index[idx_list], col] = np.nan
    return df


# ---- _is_startup tests ----


class TestIsStartup:
    """Startup detection: DMC/DC NaN at row 0 with all inputs present."""

    def test_startup_dmc_at_row0_all_inputs_present(self):
        """DMC NaN at row 0, inputs present → startup."""
        df = _make_hourly(rows=10, dmc_nan=[0, 1, 2])
        assert _is_startup(0, 3, "dmc", df, ["air_temperature_c", "relative_humidity_pct"]) is True

    def test_startup_dc_at_row0_all_inputs_present(self):
        """DC NaN at row 0, inputs present → startup."""
        df = _make_hourly(rows=10, dc_nan=[0, 1])
        assert _is_startup(0, 2, "dc", df, ["air_temperature_c"]) is True

    def test_not_startup_ffmc(self):
        """FFMC is never a startup break."""
        df = _make_hourly(rows=10, ffmc_nan=[0, 1])
        assert _is_startup(0, 2, "ffmc", df, ["air_temperature_c", "relative_humidity_pct", "wind_speed_kmh"]) is False

    def test_not_startup_not_at_row0(self):
        """Break at row 50 is not startup."""
        df = _make_hourly(rows=100, dmc_nan=[50, 51])
        assert _is_startup(50, 52, "dmc", df, ["air_temperature_c", "relative_humidity_pct"]) is False

    def test_not_startup_input_missing(self):
        """DMC NaN at row 0 but RH also NaN → not startup."""
        df = _make_hourly(rows=10, dmc_nan=[0, 1], rh_nan=[0, 1])
        assert _is_startup(0, 2, "dmc", df, ["air_temperature_c", "relative_humidity_pct"]) is False

    def test_not_startup_too_long(self):
        """DMC NaN for 30 rows at start → not startup (exceeds 24-row window)."""
        df = _make_hourly(rows=50, dmc_nan=list(range(30)))
        assert _is_startup(0, 30, "dmc", df, ["air_temperature_c", "relative_humidity_pct"]) is False


# ---- _find_cascade_cause tests ----


class TestFindCascadeCause:
    """Cascade detection: scan backwards to find original missing input."""

    def test_cascade_from_rh_gap(self):
        """RH NaN at rows 10-15, DC NaN starts at row 20 → cascade from RH."""
        df = _make_hourly(rows=50, dc_nan=list(range(20, 25)), rh_nan=list(range(10, 16)))
        ts = pd.to_datetime(df["timestamp_utc"], utc=True)
        input_col, origin = _find_cascade_cause(
            20, "dc", df, ts, ["air_temperature_c"]
        )
        assert input_col == "relative_humidity_pct"
        assert origin is not None

    def test_cascade_from_temp_gap(self):
        """Temp NaN upstream, DMC NaN downstream → cascade from temp."""
        df = _make_hourly(rows=50, dmc_nan=list(range(30, 33)), temp_nan=list(range(25, 28)))
        ts = pd.to_datetime(df["timestamp_utc"], utc=True)
        input_col, origin = _find_cascade_cause(
            30, "dmc", df, ts, ["air_temperature_c", "relative_humidity_pct"]
        )
        assert input_col == "air_temperature_c"
        assert origin is not None

    def test_no_cascade_no_prior_gaps(self):
        """No prior input gaps → no cascade found."""
        df = _make_hourly(rows=50, dc_nan=list(range(20, 22)))
        ts = pd.to_datetime(df["timestamp_utc"], utc=True)
        input_col, origin = _find_cascade_cause(
            20, "dc", df, ts, ["air_temperature_c"]
        )
        assert input_col is None
        assert origin is None

    def test_ffmc_never_cascades(self):
        """FFMC breaks are never attributed to cascades."""
        df = _make_hourly(rows=50, ffmc_nan=[20, 21], rh_nan=[15, 16])
        ts = pd.to_datetime(df["timestamp_utc"], utc=True)
        input_col, origin = _find_cascade_cause(
            20, "ffmc", df, ts, ["air_temperature_c", "relative_humidity_pct", "wind_speed_kmh"]
        )
        assert input_col is None
        assert origin is None

    def test_cascade_picks_most_recent_gap(self):
        """When multiple prior gaps exist, picks the most recent one."""
        df = _make_hourly(
            rows=100,
            dc_nan=list(range(60, 63)),
            rh_nan=list(range(30, 35)),  # older gap
            temp_nan=list(range(55, 58)),  # more recent gap
        )
        ts = pd.to_datetime(df["timestamp_utc"], utc=True)
        input_col, origin = _find_cascade_cause(
            60, "dc", df, ts, ["air_temperature_c"]
        )
        # Temp gap at row 57 is more recent than RH gap at row 34.
        assert input_col == "air_temperature_c"

    def test_cascade_origin_timestamp(self):
        """Cascade origin timestamp matches the last NaN row of the cause."""
        df = _make_hourly(rows=50, dmc_nan=list(range(20, 23)), rh_nan=[15, 16, 17])
        ts = pd.to_datetime(df["timestamp_utc"], utc=True)
        _, origin = _find_cascade_cause(
            20, "dmc", df, ts, ["air_temperature_c", "relative_humidity_pct"]
        )
        # Origin should be the timestamp of row 17 (last RH NaN).
        expected_ts = ts.iloc[17].isoformat()
        assert origin == expected_ts

    def test_cascade_at_row0_rh_nan(self):
        """DC break at row 0 with RH NaN at row 0 → cascade from RH.

        DC's direct input (temp) is present, but FFMC input (RH) is NaN.
        The cascade scanner must check at start_idx, not just backwards.
        """
        df = _make_hourly(rows=50, dc_nan=list(range(0, 10)), rh_nan=list(range(0, 15)))
        ts = pd.to_datetime(df["timestamp_utc"], utc=True)
        input_col, origin = _find_cascade_cause(
            0, "dc", df, ts, ["air_temperature_c"]
        )
        assert input_col == "relative_humidity_pct"
        assert origin is not None
        # Origin should be row 0 timestamp.
        assert origin == ts.iloc[0].isoformat()


# ---- diagnose_chain_breaks integration tests ----


class TestDiagnoseChainBreaks:
    """End-to-end diagnostics with root cause attribution."""

    def test_startup_break_reported(self):
        """Startup break is correctly identified and tagged."""
        df = _make_hourly(rows=10, dmc_nan=[0, 1, 2])
        breaks = diagnose_chain_breaks(df, "TestStation")
        assert len(breaks) == 1
        assert breaks[0].cause == "startup"
        assert breaks[0].missing_input == "n/a"
        assert breaks[0].code == "dmc"
        assert breaks[0].cascade_origin is None

    def test_cascade_break_reported(self):
        """Cascade break gets cascade: prefix and origin timestamp."""
        df = _make_hourly(rows=50, dc_nan=list(range(20, 24)), rh_nan=list(range(10, 15)))
        breaks = diagnose_chain_breaks(df, "TestStation")
        dc_breaks = [b for b in breaks if b.code == "dc"]
        assert len(dc_breaks) == 1
        assert dc_breaks[0].cause == "input_missing"
        assert "relative_humidity_pct" in dc_breaks[0].missing_input
        assert dc_breaks[0].cascade_origin is not None

    def test_no_unknown_causes_with_cascade(self):
        """Breaks that previously showed 'unknown' now get attributed."""
        # RH gap causes FFMC NaN, which cascades to DMC/DC.
        # By the time DMC NaN appears, RH is no longer NaN.
        df = _make_hourly(rows=60, rh_nan=list(range(5, 10)))
        # FFMC will NaN where RH is NaN (rows 5-9)
        df.loc[df.index[5:10], "ffmc"] = np.nan
        # DMC/DC cascade: they depend on prior FFMC being valid.
        # DMC NaN starts after the RH gap.
        df.loc[df.index[10:15], "dmc"] = np.nan
        df.loc[df.index[10:15], "dc"] = np.nan

        breaks = diagnose_chain_breaks(df, "TestStation")
        dmc_breaks = [b for b in breaks if b.code == "dmc"]
        dc_breaks = [b for b in breaks if b.code == "dc"]

        # DMC and DC should not have "unknown" missing_input.
        for b in dmc_breaks + dc_breaks:
            assert b.missing_input != "unknown", (
                f"{b.code} break at {b.break_start} has unknown cause"
            )

    def test_direct_input_missing_unchanged(self):
        """Breaks with missing inputs at start_idx work as before."""
        df = _make_hourly(rows=50, ffmc_nan=[20, 21, 22], rh_nan=[20, 21, 22])
        breaks = diagnose_chain_breaks(df, "TestStation")
        ffmc_breaks = [b for b in breaks if b.code == "ffmc"]
        assert len(ffmc_breaks) == 1
        assert ffmc_breaks[0].missing_input == "relative_humidity_pct"
        assert ffmc_breaks[0].cascade_origin is None

    def test_no_breaks_clean_data(self):
        """Clean data produces no breaks."""
        df = _make_hourly(rows=100)
        breaks = diagnose_chain_breaks(df, "TestStation")
        assert len(breaks) == 0


# ---- chain_breaks_to_dataframe tests ----


class TestChainBreaksToDataFrame:
    """DataFrame output includes cascade_origin column."""

    def test_empty_returns_schema(self):
        df = chain_breaks_to_dataframe([])
        assert "cascade_origin" in df.columns
        assert len(df) == 0

    def test_cascade_origin_in_output(self):
        breaks = [
            ChainBreak(
                station="X", code="dc",
                break_start="2023-06-01T00:00:00+00:00",
                break_end="2023-06-01T05:00:00+00:00",
                cause="input_missing",
                missing_input="cascade:relative_humidity_pct",
                rows_affected=5,
                cascade_origin="2023-05-31T20:00:00+00:00",
            )
        ]
        df = chain_breaks_to_dataframe(breaks)
        assert len(df) == 1
        assert df.iloc[0]["cascade_origin"] == "2023-05-31T20:00:00+00:00"

    def test_startup_no_cascade_origin(self):
        breaks = [
            ChainBreak(
                station="X", code="dmc",
                break_start="2023-06-01T00:00:00+00:00",
                break_end="2023-06-01T03:00:00+00:00",
                cause="startup",
                missing_input="n/a",
                rows_affected=3,
                cascade_origin=None,
            )
        ]
        df = chain_breaks_to_dataframe(breaks)
        assert pd.isna(df.iloc[0]["cascade_origin"])
