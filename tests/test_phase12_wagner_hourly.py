from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _make_hourly_frame(start_utc: str, periods: int = 48) -> pd.DataFrame:
    timestamps = pd.date_range(start_utc, periods=periods, freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "timestamp_utc": timestamps,
            "station": ["greenwich"] * periods,
            "air_temperature_c": [20.0] * periods,
            "relative_humidity_pct": [45.0] * periods,
            "wind_speed_kmh": [15.0] * periods,
            "rain_mm": [0.0] * periods,
        }
    )


def test_hffmc_handles_subthreshold_rain_and_returns_finite_values():
    from pea_met_network.cleaning import _hffmc_calc

    hourly = _make_hourly_frame("2024-07-01T00:00:00Z", periods=4)
    hourly["rain_mm"] = [0.0, 0.2, 0.0, 0.0]

    ffmc_hourly = _hffmc_calc(
        hourly["air_temperature_c"].to_numpy(float),
        hourly["relative_humidity_pct"].to_numpy(float),
        hourly["wind_speed_kmh"].to_numpy(float),
        hourly["rain_mm"].to_numpy(float),
    )

    assert len(ffmc_hourly) == 4
    assert pd.notna(ffmc_hourly).all()
    assert (ffmc_hourly >= 0).all()


def test_daily_dmc_dc_calc_repeats_values_per_local_date_with_source_date():
    from pea_met_network.cleaning import _daily_dmc_dc_calc

    hourly = _make_hourly_frame("2024-07-01T00:00:00Z", periods=48)
    hourly.loc[10:12, "rain_mm"] = [1.0, 2.0, 3.0]

    dmc, dc, source_dates = _daily_dmc_dc_calc(hourly)
    result = pd.DataFrame(
        {
            "timestamp_utc": hourly["timestamp_utc"],
            "dmc": dmc,
            "dc": dc,
            "source": source_dates,
        }
    )

    for _, group in result.groupby("source"):
        assert group["dmc"].nunique(dropna=True) == 1
        assert group["dc"].nunique(dropna=True) == 1

    assert result["source"].nunique() >= 2


def test_calculate_fwi_hourly_outputs_audit_column_and_daily_step_codes():
    from pea_met_network.cleaning import calculate_fwi_hourly

    hourly = _make_hourly_frame("2024-07-01T00:00:00Z", periods=48)
    result = calculate_fwi_hourly(hourly)

    assert "dmc_dc_source_date" in result.columns
    assert result["dmc_dc_source_date"].nunique() >= 2

    for _, group in result.groupby("dmc_dc_source_date"):
        assert group["dmc"].nunique(dropna=True) == 1
        assert group["dc"].nunique(dropna=True) == 1


def test_config_default_is_hourly_and_station_latitudes_present():
    config_path = PROJECT_ROOT / "docs" / "cleaning-config.json"
    config = json.loads(config_path.read_text())
    assert config["fwi"]["fwi_mode"] == "hourly"
    assert "station_latitudes" in config["fwi"]
