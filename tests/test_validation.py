"""Tests for pea_met_network.validation — Stanhope validation functions."""

import pandas as pd
import pytest

from pea_met_network.validation import (
    compare_station_data,
    validate_against_reference,
)


@pytest.fixture
def stanhope_daily():
    """Sample Stanhope daily data."""
    return pd.DataFrame(
        {
            "timestamp_utc": pd.to_datetime(
                ["2024-06-01", "2024-06-02", "2024-06-03"], utc=True
            ).date,
            "ffmc": [80.0, 82.0, 78.0],
            "dmc": [20.0, 22.0, 19.0],
            "dc": [100.0, 105.0, 98.0],
            "isi": [5.0, 6.0, 4.5],
            "bui": [25.0, 27.0, 24.0],
            "fwi": [10.0, 12.0, 9.0],
        }
    )


@pytest.fixture
def greenwich_daily():
    """Sample Greenwich daily data overlapping with Stanhope."""
    return pd.DataFrame(
        {
            "timestamp_utc": pd.to_datetime(
                ["2024-06-01", "2024-06-02", "2024-06-03"], utc=True
            ).date,
            "ffmc": [81.0, 83.0, 79.0],
            "dmc": [21.0, 23.0, 20.0],
            "dc": [102.0, 107.0, 100.0],
            "isi": [5.2, 6.1, 4.6],
            "bui": [26.0, 28.0, 25.0],
            "fwi": [10.5, 12.3, 9.2],
        }
    )


class TestCompareStationData:
    def test_returns_overlap_days(
        self, stanhope_daily, greenwich_daily
    ):
        result = compare_station_data(
            stanhope_daily, greenwich_daily
        )
        assert len(result) == 3

    def test_computes_fwi_mae(
        self, stanhope_daily, greenwich_daily
    ):
        merged = compare_station_data(
            stanhope_daily, greenwich_daily
        )
        fwi_diff = (merged["fwi_ref"] - merged["fwi_cmp"]).abs()
        assert fwi_diff.mean() < 1.0

    def test_computes_all_fwi_components(
        self, stanhope_daily, greenwich_daily
    ):
        merged = compare_station_data(
            stanhope_daily, greenwich_daily
        )
        for col in ["ffmc", "dmc", "dc", "isi", "bui", "fwi"]:
            assert f"{col}_ref" in merged.columns
            assert f"{col}_cmp" in merged.columns

    def test_no_overlap(self, stanhope_daily):
        no_overlap = pd.DataFrame(
            {
                "timestamp_utc": pd.to_datetime(
                    ["2025-01-01"], utc=True
                ).date,
                "ffmc": [80.0],
                "dmc": [20.0],
                "dc": [100.0],
                "isi": [5.0],
                "bui": [25.0],
                "fwi": [10.0],
            }
        )
        result = compare_station_data(
            stanhope_daily, no_overlap
        )
        assert len(result) == 0

    def test_empty_station_df(self, stanhope_daily):
        result = compare_station_data(
            stanhope_daily, pd.DataFrame()
        )
        assert len(result) == 0

    def test_empty_stanhope_df(self, greenwich_daily):
        result = compare_station_data(
            pd.DataFrame(), greenwich_daily
        )
        assert len(result) == 0


class TestValidateAgainstReference:
    def test_delegates_to_compare(
        self, stanhope_daily, greenwich_daily
    ):
        direct = compare_station_data(
            stanhope_daily, greenwich_daily
        )
        via_validate = validate_against_reference(
            "greenwich", stanhope_daily, greenwich_daily
        )
        # validate_against_reference returns a dict with
        # station and overlap_days
        assert via_validate["station"] == "greenwich"
        assert via_validate["overlap_days"] == len(direct)

    def test_returns_station_name(
        self, stanhope_daily, greenwich_daily
    ):
        result = validate_against_reference(
            "greenwich", stanhope_daily, greenwich_daily
        )
        assert result["station"] == "greenwich"
